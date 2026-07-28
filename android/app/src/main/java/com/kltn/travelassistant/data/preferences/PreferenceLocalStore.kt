package com.kltn.travelassistant.data.preferences

import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import com.kltn.travelassistant.feature.preferences.domain.PreferenceDocument
import java.security.MessageDigest
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.map
import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import kotlinx.serialization.SerializationException
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.JsonObject

internal data class LocalPreferenceRecord(
    val ownerKey: String,
    val document: PreferenceDocument,
    val localRevision: Long,
    val pendingSync: Boolean,
    val lastServerUpdatedAt: String?,
)

internal interface PreferenceLocalStore {
    fun observe(ownerKey: String): Flow<LocalPreferenceRecord?>

    suspend fun read(ownerKey: String): LocalPreferenceRecord?

    suspend fun saveLocalEdit(
        ownerKey: String,
        document: PreferenceDocument,
    ): LocalPreferenceRecord

    suspend fun applyServerRefresh(
        ownerKey: String,
        server: ServerPreferenceDocument,
    ): Boolean

    suspend fun completePush(
        ownerKey: String,
        expectedRevision: Long,
        server: ServerPreferenceDocument,
    ): Boolean
}

@Serializable
private data class LocalPreferenceWire(
    @SerialName("owner_key")
    val ownerKey: String,
    @SerialName("schema_version")
    val schemaVersion: Int,
    val preferences: JsonObject,
    @SerialName("local_revision")
    val localRevision: Long,
    @SerialName("pending_sync")
    val pendingSync: Boolean,
    @SerialName("last_server_updated_at")
    val lastServerUpdatedAt: String?,
)

internal class DataStorePreferenceLocalStore(
    private val dataStore: DataStore<Preferences>,
    private val codec: PreferenceDocumentCodec,
) : PreferenceLocalStore {
    override fun observe(ownerKey: String): Flow<LocalPreferenceRecord?> {
        validateOwnerKey(ownerKey)
        return dataStore.data.map { preferences ->
            preferences[recordKey(ownerKey)]?.let { decode(ownerKey, it) }
        }
    }

    override suspend fun read(ownerKey: String): LocalPreferenceRecord? {
        validateOwnerKey(ownerKey)
        return dataStore.data.first()[recordKey(ownerKey)]?.let {
            decode(ownerKey, it)
        }
    }

    override suspend fun saveLocalEdit(
        ownerKey: String,
        document: PreferenceDocument,
    ): LocalPreferenceRecord {
        validateOwnerKey(ownerKey)
        val normalized = codec.validate(document)
        lateinit var saved: LocalPreferenceRecord
        dataStore.edit { preferences ->
            val existing = preferences[recordKey(ownerKey)]?.let {
                decode(ownerKey, it)
            }
            if (existing?.document == normalized) {
                saved = existing
                return@edit
            }
            val nextRevision = when (existing?.localRevision) {
                null -> 1L
                Long.MAX_VALUE -> throw IllegalStateException("Preference revision exhausted")
                else -> existing.localRevision + 1L
            }
            saved = LocalPreferenceRecord(
                ownerKey = ownerKey,
                document = normalized,
                localRevision = nextRevision,
                pendingSync = true,
                lastServerUpdatedAt = existing?.lastServerUpdatedAt,
            )
            preferences[recordKey(ownerKey)] = encode(saved)
        }
        return saved
    }

    override suspend fun applyServerRefresh(
        ownerKey: String,
        server: ServerPreferenceDocument,
    ): Boolean {
        validateOwnerKey(ownerKey)
        val normalized = codec.validate(server.document)
        var applied = false
        dataStore.edit { preferences ->
            val existing = preferences[recordKey(ownerKey)]?.let {
                decode(ownerKey, it)
            }
            if (existing?.pendingSync == true) return@edit
            val updated = LocalPreferenceRecord(
                ownerKey = ownerKey,
                document = normalized,
                localRevision = existing?.localRevision ?: 0L,
                pendingSync = false,
                lastServerUpdatedAt = server.updatedAt,
            )
            if (existing != updated) {
                preferences[recordKey(ownerKey)] = encode(updated)
            }
            applied = true
        }
        return applied
    }

    override suspend fun completePush(
        ownerKey: String,
        expectedRevision: Long,
        server: ServerPreferenceDocument,
    ): Boolean {
        validateOwnerKey(ownerKey)
        val normalized = codec.validate(server.document)
        var completed = false
        dataStore.edit { preferences ->
            val existing = preferences[recordKey(ownerKey)]?.let {
                decode(ownerKey, it)
            } ?: return@edit
            if (existing.localRevision != expectedRevision) return@edit
            preferences[recordKey(ownerKey)] = encode(
                existing.copy(
                    document = normalized,
                    pendingSync = false,
                    lastServerUpdatedAt = server.updatedAt,
                ),
            )
            completed = true
        }
        return completed
    }

    private fun encode(record: LocalPreferenceRecord): String =
        strictPreferenceJson().encodeToString(
            LocalPreferenceWire.serializer(),
            LocalPreferenceWire(
                ownerKey = record.ownerKey,
                schemaVersion = record.document.schemaVersion,
                preferences = record.document.preferences,
                localRevision = record.localRevision,
                pendingSync = record.pendingSync,
                lastServerUpdatedAt = record.lastServerUpdatedAt,
            ),
        )

    private fun decode(ownerKey: String, raw: String): LocalPreferenceRecord {
        val wire = try {
            strictPreferenceJson().decodeFromString(
                LocalPreferenceWire.serializer(),
                raw,
            )
        } catch (exception: SerializationException) {
            throw InvalidPreferenceDocumentException()
        } catch (exception: IllegalArgumentException) {
            throw InvalidPreferenceDocumentException()
        }
        if (
            wire.ownerKey != ownerKey ||
            wire.localRevision < 0 ||
            !OWNER_KEY_PATTERN.matches(wire.ownerKey)
        ) {
            throw InvalidPreferenceDocumentException()
        }
        val document = codec.validate(
            PreferenceDocument(
                schemaVersion = wire.schemaVersion,
                preferences = wire.preferences,
            ),
        )
        val timestamp = wire.lastServerUpdatedAt?.let(codec::normalizeServerTimestamp)
        return LocalPreferenceRecord(
            ownerKey = wire.ownerKey,
            document = document,
            localRevision = wire.localRevision,
            pendingSync = wire.pendingSync,
            lastServerUpdatedAt = timestamp,
        )
    }

    private fun recordKey(ownerKey: String): Preferences.Key<String> =
        stringPreferencesKey("account_$ownerKey")

    private fun validateOwnerKey(ownerKey: String) {
        if (!OWNER_KEY_PATTERN.matches(ownerKey)) {
            throw IllegalArgumentException("Invalid preference owner key")
        }
    }

    private companion object {
        val OWNER_KEY_PATTERN = Regex("^[0-9a-f]{64}$")
    }
}

internal object PreferenceOwnerKey {
    fun fromUid(uid: String): String {
        require(uid.isNotBlank())
        return MessageDigest.getInstance("SHA-256")
            .digest(uid.toByteArray(Charsets.UTF_8))
            .joinToString(separator = "") { byte ->
                "%02x".format(byte.toInt() and 0xff)
            }
    }
}
