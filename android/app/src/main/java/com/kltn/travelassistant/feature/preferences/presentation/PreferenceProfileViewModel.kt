package com.kltn.travelassistant.feature.preferences.presentation

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.kltn.travelassistant.feature.preferences.domain.BudgetPreference
import com.kltn.travelassistant.feature.preferences.domain.MAX_TRAVEL_INTERESTS
import com.kltn.travelassistant.feature.preferences.domain.PreferenceRepository
import com.kltn.travelassistant.feature.preferences.domain.PreferenceSyncState
import com.kltn.travelassistant.feature.preferences.domain.PreferenceUpdateResult
import com.kltn.travelassistant.feature.preferences.domain.TravelInterest
import com.kltn.travelassistant.feature.preferences.domain.TravelPace
import com.kltn.travelassistant.feature.preferences.domain.TravelPreferenceProfile
import com.kltn.travelassistant.feature.preferences.domain.documentOrNull
import com.kltn.travelassistant.feature.preferences.domain.toTravelPreferenceProfileOrNull
import dagger.hilt.android.lifecycle.HiltViewModel
import javax.inject.Inject
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

@HiltViewModel
class PreferenceProfileViewModel @Inject constructor(
    private val repository: PreferenceRepository,
) : ViewModel() {
    private val mutableUiState = MutableStateFlow(PreferenceProfileUiState())
    val uiState: StateFlow<PreferenceProfileUiState> = mutableUiState.asStateFlow()

    init {
        viewModelScope.launch {
            repository.state.collect(::applyRepositoryState)
        }
    }

    fun beginEdit() {
        mutableUiState.update { state ->
            if (!state.isVisible || state.isSaving) state else state.copy(
                draftProfile = state.savedProfile,
                isEditing = true,
                message = null,
            )
        }
    }

    fun cancelEdit() {
        mutableUiState.update { state ->
            state.copy(
                draftProfile = state.savedProfile,
                isEditing = false,
                showResetConfirmation = false,
                message = null,
            )
        }
    }

    fun toggleInterest(interest: TravelInterest) {
        mutableUiState.update { state ->
            if (!state.isEditing || state.isSaving) return@update state
            val selected = state.draftProfile.interests
            if (interest !in selected && selected.size >= MAX_TRAVEL_INTERESTS) {
                return@update state.copy(message = PreferenceProfileMessage.MAXIMUM_INTERESTS)
            }
            state.copy(
                draftProfile = state.draftProfile.copy(
                    interests = if (interest in selected) selected - interest else selected + interest,
                ),
                message = null,
            )
        }
    }

    fun selectPace(pace: TravelPace?) {
        mutableUiState.update { state ->
            if (!state.isEditing || state.isSaving) state else state.copy(
                draftProfile = state.draftProfile.copy(pace = pace),
                message = null,
            )
        }
    }

    fun selectBudget(budget: BudgetPreference?) {
        mutableUiState.update { state ->
            if (!state.isEditing || state.isSaving) state else state.copy(
                draftProfile = state.draftProfile.copy(budgetPreference = budget),
                message = null,
            )
        }
    }

    fun save() {
        if (!mutableUiState.value.isEditing) return
        persist(
            profile = mutableUiState.value.draftProfile,
            successMessage = PreferenceProfileMessage.SAVED_LOCALLY,
        )
    }

    fun requestReset() {
        mutableUiState.update { state ->
            if (!state.isVisible || state.isSaving) state else state.copy(
                showResetConfirmation = true,
                message = null,
            )
        }
    }

    fun dismissReset() {
        mutableUiState.update { it.copy(showResetConfirmation = false) }
    }

    fun confirmReset() {
        mutableUiState.update { it.copy(showResetConfirmation = false) }
        persist(
            profile = TravelPreferenceProfile(),
            successMessage = PreferenceProfileMessage.RESET_LOCALLY,
        )
    }

    fun retry() = repository.retry()

    private fun persist(
        profile: TravelPreferenceProfile,
        successMessage: PreferenceProfileMessage,
    ) {
        val state = mutableUiState.value
        if (!state.isVisible || state.isSaving) return
        mutableUiState.update { it.copy(isSaving = true, message = null) }
        viewModelScope.launch {
            when (repository.updateLocal(profile.toDocument())) {
                PreferenceUpdateResult.SavedAndQueued -> mutableUiState.update {
                    it.copy(
                        savedProfile = profile,
                        draftProfile = profile,
                        isEditing = false,
                        isSaving = false,
                        isLegacyDocument = false,
                        message = successMessage,
                    )
                }
                PreferenceUpdateResult.SignedOut -> mutableUiState.value =
                    PreferenceProfileUiState()
                PreferenceUpdateResult.InvalidDocument -> mutableUiState.update {
                    it.copy(
                        isSaving = false,
                        message = PreferenceProfileMessage.INVALID_DOCUMENT,
                    )
                }
                PreferenceUpdateResult.StorageFailure -> mutableUiState.update {
                    it.copy(
                        isSaving = false,
                        message = PreferenceProfileMessage.STORAGE_FAILURE,
                    )
                }
            }
        }
    }

    private fun applyRepositoryState(syncState: PreferenceSyncState) {
        if (syncState is PreferenceSyncState.SignedOut) {
            mutableUiState.value = PreferenceProfileUiState()
            return
        }
        val document = syncState.documentOrNull()
        val profile = document?.toTravelPreferenceProfileOrNull() ?: TravelPreferenceProfile()
        mutableUiState.update { current ->
            current.copy(
                isVisible = true,
                status = syncState.toProfileStatus(),
                savedProfile = profile,
                draftProfile = if (current.isEditing) current.draftProfile else profile,
                isLegacyDocument = document?.preferences?.isNotEmpty() == true &&
                    document.toTravelPreferenceProfileOrNull() == null,
            )
        }
    }
}

private fun PreferenceSyncState.toProfileStatus(): PreferenceProfileStatus = when (this) {
    PreferenceSyncState.SignedOut,
    PreferenceSyncState.LoadingLocal,
    -> PreferenceProfileStatus.LOADING
    is PreferenceSyncState.LocalCurrent -> PreferenceProfileStatus.CURRENT
    is PreferenceSyncState.PendingOffline -> PreferenceProfileStatus.PENDING_OFFLINE
    is PreferenceSyncState.Synchronizing -> PreferenceProfileStatus.SYNCHRONIZING
    is PreferenceSyncState.Synchronized -> PreferenceProfileStatus.SYNCHRONIZED
    is PreferenceSyncState.RetryableFailure -> PreferenceProfileStatus.RETRYABLE_FAILURE
    PreferenceSyncState.AuthenticationFailure -> PreferenceProfileStatus.AUTHENTICATION_FAILURE
    PreferenceSyncState.InvalidDocument -> PreferenceProfileStatus.INVALID_DOCUMENT
}
