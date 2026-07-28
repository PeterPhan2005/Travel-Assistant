package com.kltn.travelassistant.data.preferences

import com.kltn.travelassistant.feature.preferences.domain.PreferenceDocument
import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.async
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.test.runTest
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class PreferenceSyncEngineTest {
    @Test
    fun pendingLocalSnapshotPushesBeforeAnyGetAndPersistsTimestamp() = runTest {
        val local = FakeLocalStore(pendingRecord(revision = 3, value = "latest"))
        val api = FakeApi()
        val engine = PreferenceSyncEngine(FakeSession(), local, api)

        val outcome = engine.synchronizeCurrentAccount()

        assertEquals(PreferenceSyncOutcome.SUCCESS, outcome)
        assertEquals(listOf("put"), api.operations)
        assertEquals("latest", api.lastPutValue)
        assertFalse(requireNotNull(local.record).pendingSync)
        assertEquals(SERVER_TIME, local.record?.lastServerUpdatedAt)
    }

    @Test
    fun noPendingLocalDataRefreshesFromServer() = runTest {
        val local = FakeLocalStore(
            pendingRecord(revision = 2, value = "cached").copy(pendingSync = false),
        )
        val api = FakeApi(serverValue = "server")
        val engine = PreferenceSyncEngine(FakeSession(), local, api)

        val outcome = engine.synchronizeCurrentAccount()

        assertEquals(PreferenceSyncOutcome.SUCCESS, outcome)
        assertEquals(listOf("get"), api.operations)
        assertEquals("server", local.record?.value())
    }

    @Test
    fun inFlightOlderSuccessCannotClearNewerRevision() = runTest {
        val local = FakeLocalStore(pendingRecord(revision = 1, value = "old"))
        val api = FakeApi(pausePut = true)
        val engine = PreferenceSyncEngine(FakeSession(), local, api)

        val synchronization = async { engine.synchronizeCurrentAccount() }
        api.putStarted.await()
        local.record = pendingRecord(revision = 2, value = "new")
        api.releasePut.complete(Unit)

        assertEquals(
            PreferenceSyncOutcome.NEWER_LOCAL_REVISION,
            synchronization.await(),
        )
        assertTrue(requireNotNull(local.record).pendingSync)
        assertEquals(2L, local.record?.localRevision)
        assertEquals("new", local.record?.value())
    }

    @Test
    fun pendingEditAppearingDuringGetIsNeverOverwritten() = runTest {
        val local = FakeLocalStore(null)
        val api = FakeApi(serverValue = "server", pauseGet = true)
        val engine = PreferenceSyncEngine(FakeSession(), local, api)

        val synchronization = async { engine.synchronizeCurrentAccount() }
        api.getStarted.await()
        local.record = pendingRecord(revision = 1, value = "offline")
        api.releaseGet.complete(Unit)

        assertEquals(
            PreferenceSyncOutcome.NEWER_LOCAL_REVISION,
            synchronization.await(),
        )
        assertEquals("offline", local.record?.value())
        assertTrue(requireNotNull(local.record).pendingSync)
    }

    private class FakeSession : FirebasePreferenceSession {
        override fun currentVerifiedAccount() = ActivePreferenceAccount(OWNER_KEY)

        override suspend fun idToken(
            expectedOwnerKey: String,
            forceRefresh: Boolean,
        ) = PreferenceTokenResult.Success("unused")
    }

    private class FakeApi(
        private val serverValue: String = "normalized",
        private val pausePut: Boolean = false,
        private val pauseGet: Boolean = false,
    ) : PreferenceApi {
        val operations = mutableListOf<String>()
        val putStarted = CompletableDeferred<Unit>()
        val releasePut = CompletableDeferred<Unit>()
        val getStarted = CompletableDeferred<Unit>()
        val releaseGet = CompletableDeferred<Unit>()
        var lastPutValue: String? = null

        override suspend fun get(ownerKey: String): ServerPreferenceDocument {
            operations += "get"
            getStarted.complete(Unit)
            if (pauseGet) releaseGet.await()
            return serverDocument(serverValue, updatedAt = SERVER_TIME)
        }

        override suspend fun put(
            ownerKey: String,
            document: PreferenceDocument,
        ): ServerPreferenceDocument {
            operations += "put"
            lastPutValue = document.preferences["value"]?.let {
                (it as JsonPrimitive).content
            }
            putStarted.complete(Unit)
            if (pausePut) releasePut.await()
            return ServerPreferenceDocument(document, SERVER_TIME)
        }
    }

    private class FakeLocalStore(
        initial: LocalPreferenceRecord?,
    ) : PreferenceLocalStore {
        val flow = MutableStateFlow(initial)
        var record: LocalPreferenceRecord?
            get() = flow.value
            set(value) {
                flow.value = value
            }

        override fun observe(ownerKey: String): Flow<LocalPreferenceRecord?> = flow

        override suspend fun read(ownerKey: String): LocalPreferenceRecord? = record

        override suspend fun saveLocalEdit(
            ownerKey: String,
            document: PreferenceDocument,
        ): LocalPreferenceRecord = error("unused")

        override suspend fun applyServerRefresh(
            ownerKey: String,
            server: ServerPreferenceDocument,
        ): Boolean {
            if (record?.pendingSync == true) return false
            record = LocalPreferenceRecord(
                ownerKey = ownerKey,
                document = server.document,
                localRevision = record?.localRevision ?: 0,
                pendingSync = false,
                lastServerUpdatedAt = server.updatedAt,
            )
            return true
        }

        override suspend fun completePush(
            ownerKey: String,
            expectedRevision: Long,
            server: ServerPreferenceDocument,
        ): Boolean {
            val existing = record ?: return false
            if (existing.localRevision != expectedRevision) return false
            record = existing.copy(
                document = server.document,
                pendingSync = false,
                lastServerUpdatedAt = server.updatedAt,
            )
            return true
        }
    }

    private companion object {
        const val OWNER_KEY =
            "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
        const val SERVER_TIME = "2026-07-28T03:04:05Z"

        fun pendingRecord(revision: Long, value: String) = LocalPreferenceRecord(
            ownerKey = OWNER_KEY,
            document = PreferenceDocument(
                preferences = JsonObject(mapOf("value" to JsonPrimitive(value))),
            ),
            localRevision = revision,
            pendingSync = true,
            lastServerUpdatedAt = null,
        )

        fun serverDocument(value: String, updatedAt: String?) =
            ServerPreferenceDocument(
                PreferenceDocument(
                    preferences = JsonObject(mapOf("value" to JsonPrimitive(value))),
                ),
                updatedAt,
            )

        fun LocalPreferenceRecord.value(): String =
            (document.preferences["value"] as JsonPrimitive).content
    }
}

