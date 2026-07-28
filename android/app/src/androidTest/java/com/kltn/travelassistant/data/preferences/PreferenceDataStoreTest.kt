package com.kltn.travelassistant.data.preferences

import androidx.datastore.preferences.core.PreferenceDataStoreFactory
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import android.content.Context
import com.kltn.travelassistant.feature.preferences.domain.PreferenceDocument
import java.io.File
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.runBlocking
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class PreferenceDataStoreTest {
    private lateinit var file: File
    private var scope: CoroutineScope? = null

    @Before
    fun setUp() {
        val context = ApplicationProvider.getApplicationContext<Context>()
        file = context.filesDir.resolve("datastore/preference-test-${System.nanoTime()}.preferences_pb")
        file.parentFile?.mkdirs()
        file.delete()
    }

    @After
    fun tearDown() {
        scope?.cancel()
        file.delete()
    }

    @Test
    fun pendingEditsSurviveStoreRecreationAndAccountsStayIsolated() = runBlocking {
        val firstOwner = PreferenceOwnerKey.fromUid("firebase-account-one")
        val secondOwner = PreferenceOwnerKey.fromUid("firebase-account-two")
        val firstStore = createStore()
        firstStore.saveLocalEdit(firstOwner, document("first"))
        firstStore.saveLocalEdit(firstOwner, document("latest"))
        firstStore.saveLocalEdit(secondOwner, document("second"))

        assertTrue(requireNotNull(firstStore.read(firstOwner)).pendingSync)
        assertEquals(2L, firstStore.read(firstOwner)?.localRevision)
        assertEquals("latest", firstStore.read(firstOwner)?.value())
        assertEquals("second", firstStore.read(secondOwner)?.value())
        closeStore()

        val recreated = createStore()
        val restoredFirst = requireNotNull(recreated.read(firstOwner))
        val restoredSecond = requireNotNull(recreated.read(secondOwner))

        assertTrue(restoredFirst.pendingSync)
        assertEquals(2L, restoredFirst.localRevision)
        assertEquals("latest", restoredFirst.value())
        assertEquals("second", restoredSecond.value())
        assertFalse(file.readBytes().toString(Charsets.ISO_8859_1).contains(SENTINEL_TOKEN))
    }

    @Test
    fun refreshNeverOverwritesPendingAndMatchingRevisionAloneClearsIt() = runBlocking {
        val owner = PreferenceOwnerKey.fromUid("firebase-account")
        val store = createStore()
        val first = store.saveLocalEdit(owner, document("offline"))

        assertFalse(
            store.applyServerRefresh(owner, server("server", SERVER_TIME)),
        )
        assertEquals("offline", store.read(owner)?.value())

        store.saveLocalEdit(owner, document("newer"))
        assertFalse(
            store.completePush(owner, first.localRevision, server("old", SERVER_TIME)),
        )
        assertTrue(requireNotNull(store.read(owner)).pendingSync)
        val latestRevision = requireNotNull(store.read(owner)).localRevision

        assertTrue(
            store.completePush(owner, latestRevision, server("newer", SERVER_TIME)),
        )
        val completed = requireNotNull(store.read(owner))
        assertFalse(completed.pendingSync)
        assertEquals(SERVER_TIME, completed.lastServerUpdatedAt)
        assertEquals("newer", completed.value())
    }

    @Test
    fun absentAccountReturnsNoRecordInsteadOfAnotherAccountsDocument() = runBlocking {
        val store = createStore()
        store.saveLocalEdit(PreferenceOwnerKey.fromUid("one"), document("private"))

        assertNull(store.read(PreferenceOwnerKey.fromUid("two")))
    }

    private fun createStore(): DataStorePreferenceLocalStore {
        val newScope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
        scope = newScope
        return DataStorePreferenceLocalStore(
            dataStore = PreferenceDataStoreFactory.create(
                scope = newScope,
                produceFile = { file },
            ),
            codec = PreferenceDocumentCodec(),
        )
    }

    private fun closeStore() {
        scope?.cancel()
        scope = null
        Thread.sleep(50)
    }

    private fun document(value: String) = PreferenceDocument(
        preferences = JsonObject(mapOf("value" to JsonPrimitive(value))),
    )

    private fun server(value: String, updatedAt: String?) =
        ServerPreferenceDocument(document(value), updatedAt)

    private fun LocalPreferenceRecord.value(): String =
        (document.preferences["value"] as JsonPrimitive).content

    private companion object {
        const val SERVER_TIME = "2026-07-28T04:05:06Z"
        const val SENTINEL_TOKEN = "firebase-token-must-never-be-stored"
    }
}

