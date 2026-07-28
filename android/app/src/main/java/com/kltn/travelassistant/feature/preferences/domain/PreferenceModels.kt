package com.kltn.travelassistant.feature.preferences.domain

import kotlinx.coroutines.flow.StateFlow
import kotlinx.serialization.json.JsonObject

const val PREFERENCE_SCHEMA_VERSION = 1

data class PreferenceDocument(
    val schemaVersion: Int = PREFERENCE_SCHEMA_VERSION,
    val preferences: JsonObject = JsonObject(emptyMap()),
)

sealed interface PreferenceSyncState {
    data object SignedOut : PreferenceSyncState

    data object LoadingLocal : PreferenceSyncState

    data class LocalCurrent(val document: PreferenceDocument) : PreferenceSyncState

    data class PendingOffline(val document: PreferenceDocument) : PreferenceSyncState

    data class Synchronizing(val document: PreferenceDocument) : PreferenceSyncState

    data class Synchronized(
        val document: PreferenceDocument,
        val serverUpdatedAt: String,
    ) : PreferenceSyncState

    data class RetryableFailure(val document: PreferenceDocument) : PreferenceSyncState

    data object AuthenticationFailure : PreferenceSyncState

    data object InvalidDocument : PreferenceSyncState
}

sealed interface PreferenceUpdateResult {
    data object SavedAndQueued : PreferenceUpdateResult

    data object SignedOut : PreferenceUpdateResult

    data object InvalidDocument : PreferenceUpdateResult

    data object StorageFailure : PreferenceUpdateResult
}

interface PreferenceRepository {
    val state: StateFlow<PreferenceSyncState>

    suspend fun updateLocal(document: PreferenceDocument): PreferenceUpdateResult

    fun refresh()

    fun retry()
}

