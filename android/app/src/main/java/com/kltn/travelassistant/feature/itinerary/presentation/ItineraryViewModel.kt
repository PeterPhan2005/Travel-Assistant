package com.kltn.travelassistant.feature.itinerary.presentation

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.kltn.travelassistant.feature.itinerary.domain.ItineraryCity
import com.kltn.travelassistant.feature.itinerary.domain.ItineraryDraft
import com.kltn.travelassistant.feature.itinerary.domain.ItineraryDraftFailure
import com.kltn.travelassistant.feature.itinerary.domain.ItineraryDraftGenerationResult
import com.kltn.travelassistant.feature.itinerary.domain.ItineraryDraftGenerator
import com.kltn.travelassistant.feature.itinerary.domain.ItineraryDraftRequest
import com.kltn.travelassistant.feature.itinerary.domain.ItineraryLocationSnapshot
import com.kltn.travelassistant.feature.itinerary.domain.ItinerarySaveBoundary
import com.kltn.travelassistant.feature.itinerary.domain.ItinerarySaveResult
import com.kltn.travelassistant.feature.itinerary.domain.SavedItineraryDeleteResult
import com.kltn.travelassistant.feature.itinerary.domain.SavedItineraryLibraryState
import com.kltn.travelassistant.feature.itinerary.domain.SavedItineraryRepository
import com.kltn.travelassistant.feature.itinerary.domain.isValidDraftForRequest
import dagger.hilt.android.lifecycle.HiltViewModel
import javax.inject.Inject
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Job
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.emptyFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

@HiltViewModel
class ItineraryViewModel @Inject internal constructor(
    private val generator: ItineraryDraftGenerator,
    private val saveBoundary: ItinerarySaveBoundary,
    private val savedItineraryRepository: SavedItineraryRepository = EmptySavedItineraryRepository,
) : ViewModel() {
    private val mutableUiState = MutableStateFlow(ItineraryUiState())
    internal val uiState: StateFlow<ItineraryUiState> = mutableUiState.asStateFlow()

    private var generationJob: Job? = null
    private var generationId = 0L
    private var retrySnapshot: ItineraryDraftRequest? = null
    private var saveJob: Job? = null
    private var nextSaveAttemptId = 0L
    private var activeSaveAttemptId: Long? = null
    private var selectedSavedItineraryId: String? = null
    private var deleteJob: Job? = null

    init {
        viewModelScope.launch {
            savedItineraryRepository.observeLibrary().collect { libraryState ->
                mutableUiState.update { state ->
                    val opened = (libraryState as? SavedItineraryLibraryState.Content)
                        ?.itineraries
                        ?.firstOrNull { it.id == selectedSavedItineraryId }
                    if (selectedSavedItineraryId != null && opened == null) {
                        selectedSavedItineraryId = null
                    }
                    state.copy(
                        libraryState = libraryState,
                        openedSavedItinerary = opened,
                    )
                }
            }
        }
    }

    internal fun onCitySelected(city: ItineraryCity) {
        updateForm { copy(city = city) }
    }

    internal fun onLocalDateChanged(value: String) {
        updateForm { copy(localDate = value) }
    }

    internal fun onStartTimeChanged(value: String) {
        updateForm { copy(startLocalTime = value) }
    }

    internal fun onEndTimeChanged(value: String) {
        updateForm { copy(endLocalTime = value) }
    }

    internal fun onMaximumStopsChanged(value: String) {
        updateForm { copy(maximumStops = value) }
    }

    internal fun onNotesChanged(value: String) {
        updateForm { copy(notes = value) }
    }

    internal fun generate(
        currentLocation: ItineraryLocationSnapshot?,
        isOnline: Boolean = true,
    ) {
        if (generationJob?.isActive == true) return
        when (
            val validation = validateItineraryForm(
                form = mutableUiState.value.form,
                currentLocation = currentLocation,
            )
        ) {
            is ItineraryFormValidationResult.Invalid -> {
                retrySnapshot = null
                mutableUiState.update { state ->
                    state.copy(
                        fieldErrors = validation.errors,
                        generationState = ItineraryGenerationUiState.Idle,
                        saveState = ItinerarySaveUiState.Idle,
                    )
                }
            }
            is ItineraryFormValidationResult.Valid -> {
                retrySnapshot = validation.request
                mutableUiState.update { state ->
                    state.copy(fieldErrors = ItineraryFieldErrors())
                }
                if (isOnline) {
                    execute(validation.request)
                } else {
                    mutableUiState.update { state ->
                        state.copy(
                            generationState = ItineraryGenerationUiState.Error(
                                ItineraryDraftFailure.OFFLINE,
                            ),
                            saveState = ItinerarySaveUiState.Idle,
                        )
                    }
                }
            }
        }
    }

    internal fun retry(isOnline: Boolean = true) {
        if (generationJob?.isActive == true) return
        val error = mutableUiState.value.generationState as? ItineraryGenerationUiState.Error
            ?: return
        if (!error.reason.retryable) return
        val request = retrySnapshot ?: return
        if (isOnline) {
            execute(request)
        } else {
            mutableUiState.update { state ->
                state.copy(
                    generationState = ItineraryGenerationUiState.Error(
                        ItineraryDraftFailure.OFFLINE,
                    ),
                )
            }
        }
    }

    internal fun cancelGeneration() {
        cancelActiveGeneration(showCancelled = true)
    }

    internal fun onScreenLeft() {
        cancelActiveGeneration(showCancelled = true)
        cancelActiveSave()
    }

    internal fun onAppBackgrounded() {
        cancelActiveGeneration(showCancelled = true)
        cancelActiveSave()
    }

    internal fun save() {
        if (saveJob?.isActive == true) return
        val draft = (
            mutableUiState.value.generationState as? ItineraryGenerationUiState.Content
            )?.draft ?: return
        val saveAttemptId = ++nextSaveAttemptId
        activeSaveAttemptId = saveAttemptId
        mutableUiState.update { state ->
            state.copy(saveState = ItinerarySaveUiState.Saving)
        }
        saveJob = viewModelScope.launch {
            val result = try {
                saveBoundary.save(draft)
            } catch (exception: CancellationException) {
                throw exception
            } catch (_: Exception) {
                ItinerarySaveResult.Failed
            }
            if (saveAttemptId != activeSaveAttemptId) return@launch
            activeSaveAttemptId = null
            saveJob = null
            mutableUiState.update { state ->
                state.copy(
                    saveState = when (result) {
                        ItinerarySaveResult.SavedLocally ->
                            ItinerarySaveUiState.SavedLocallyPendingSync
                        ItinerarySaveResult.AuthenticationRequired ->
                            ItinerarySaveUiState.AuthenticationRequired
                        ItinerarySaveResult.Failed -> ItinerarySaveUiState.Failed
                    },
                )
            }
        }
    }

    internal fun openSavedItinerary(itineraryId: String) {
        val saved = (mutableUiState.value.libraryState as? SavedItineraryLibraryState.Content)
            ?.itineraries
            ?.firstOrNull { it.id == itineraryId }
            ?: return
        selectedSavedItineraryId = saved.id
        mutableUiState.update { state ->
            state.copy(
                openedSavedItinerary = saved,
                deleteState = ItineraryDeleteUiState.Idle,
            )
        }
    }

    internal fun returnToGeneration() {
        selectedSavedItineraryId = null
        mutableUiState.update { state ->
            state.copy(
                openedSavedItinerary = null,
                deleteState = ItineraryDeleteUiState.Idle,
            )
        }
    }

    internal fun deleteOpenedSavedItinerary() {
        if (deleteJob?.isActive == true) return
        val itineraryId = mutableUiState.value.openedSavedItinerary?.id ?: return
        mutableUiState.update { state ->
            state.copy(deleteState = ItineraryDeleteUiState.Deleting)
        }
        deleteJob = viewModelScope.launch {
            val result = try {
                savedItineraryRepository.delete(itineraryId)
            } catch (exception: CancellationException) {
                throw exception
            } catch (_: Exception) {
                SavedItineraryDeleteResult.Failed
            }
            deleteJob = null
            when (result) {
                SavedItineraryDeleteResult.DeletedLocally -> returnToGeneration()
                SavedItineraryDeleteResult.AuthenticationRequired,
                SavedItineraryDeleteResult.NotFound,
                SavedItineraryDeleteResult.Failed,
                -> mutableUiState.update { state ->
                    state.copy(deleteState = ItineraryDeleteUiState.Failed)
                }
            }
        }
    }

    override fun onCleared() {
        cancelActiveGeneration(showCancelled = false)
        cancelActiveSave()
        deleteJob?.cancel()
        super.onCleared()
    }

    private fun execute(request: ItineraryDraftRequest) {
        cancelActiveSave()
        val requestId = ++generationId
        mutableUiState.update { state ->
            state.copy(
                generationState = ItineraryGenerationUiState.Loading,
                saveState = ItinerarySaveUiState.Idle,
            )
        }
        generationJob = viewModelScope.launch {
            val result = try {
                generator.generate(request)
            } catch (exception: CancellationException) {
                throw exception
            } catch (_: Exception) {
                ItineraryDraftGenerationResult.Failure(
                    ItineraryDraftFailure.INVALID_RESPONSE,
                )
            }
            if (requestId != generationId) return@launch
            generationJob = null
            mutableUiState.update { state ->
                state.copy(generationState = result.toUiState(request))
            }
        }
    }

    private fun updateForm(transform: ItineraryFormState.() -> ItineraryFormState) {
        val wasLoading = generationJob?.isActive == true
        if (wasLoading) {
            cancelActiveGeneration(showCancelled = false)
        }
        cancelActiveSave()
        retrySnapshot = null
        mutableUiState.update { state ->
            state.copy(
                form = state.form.transform(),
                fieldErrors = ItineraryFieldErrors(),
                generationState = if (wasLoading) {
                    ItineraryGenerationUiState.Cancelled
                } else {
                    ItineraryGenerationUiState.Idle
                },
                saveState = ItinerarySaveUiState.Idle,
            )
        }
    }

    private fun cancelActiveGeneration(showCancelled: Boolean) {
        val active = generationJob?.isActive == true
        if (!active) return
        generationId += 1
        generationJob?.cancel()
        generationJob = null
        if (showCancelled) {
            mutableUiState.update { state ->
                state.copy(generationState = ItineraryGenerationUiState.Cancelled)
            }
        }
    }

    private fun cancelActiveSave() {
        val activeJob = saveJob?.takeIf(Job::isActive)
        val hadActiveAttempt = activeSaveAttemptId != null
        activeSaveAttemptId = null
        activeJob?.cancel()
        saveJob = null
        if (hadActiveAttempt) {
            mutableUiState.update { state ->
                state.copy(saveState = ItinerarySaveUiState.Idle)
            }
        }
    }
}

private object EmptySavedItineraryRepository : SavedItineraryRepository {
    override fun observeLibrary() = emptyFlow<SavedItineraryLibraryState>()

    override suspend fun delete(itineraryId: String) = SavedItineraryDeleteResult.NotFound
}

private fun ItineraryDraftGenerationResult.toUiState(
    request: ItineraryDraftRequest,
): ItineraryGenerationUiState = when (this) {
    is ItineraryDraftGenerationResult.Success -> {
        if (isValidDraftForRequest(draft, request)) {
            ItineraryGenerationUiState.Content(draft)
        } else {
            ItineraryGenerationUiState.Error(ItineraryDraftFailure.INVALID_RESPONSE)
        }
    }
    is ItineraryDraftGenerationResult.Failure -> {
        if (reason == ItineraryDraftFailure.UNSUPPORTED_TRANSPORT) {
            ItineraryGenerationUiState.Unavailable
        } else {
            ItineraryGenerationUiState.Error(reason)
        }
    }
}
