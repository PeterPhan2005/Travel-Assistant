package com.kltn.travelassistant.feature.preferences.presentation

import com.kltn.travelassistant.feature.preferences.domain.TravelPreferenceProfile

data class PreferenceProfileUiState(
    val isVisible: Boolean = false,
    val status: PreferenceProfileStatus = PreferenceProfileStatus.LOADING,
    val savedProfile: TravelPreferenceProfile = TravelPreferenceProfile(),
    val draftProfile: TravelPreferenceProfile = TravelPreferenceProfile(),
    val isEditing: Boolean = false,
    val isSaving: Boolean = false,
    val isLegacyDocument: Boolean = false,
    val showResetConfirmation: Boolean = false,
    val message: PreferenceProfileMessage? = null,
)

enum class PreferenceProfileStatus {
    LOADING,
    CURRENT,
    PENDING_OFFLINE,
    SYNCHRONIZING,
    SYNCHRONIZED,
    RETRYABLE_FAILURE,
    AUTHENTICATION_FAILURE,
    INVALID_DOCUMENT,
}

enum class PreferenceProfileMessage {
    MAXIMUM_INTERESTS,
    SAVED_LOCALLY,
    RESET_LOCALLY,
    INVALID_DOCUMENT,
    STORAGE_FAILURE,
}
