package com.kltn.travelassistant.feature.itinerary.presentation

import com.kltn.travelassistant.feature.itinerary.domain.ItineraryCity
import com.kltn.travelassistant.feature.itinerary.domain.ItineraryDraft
import com.kltn.travelassistant.feature.itinerary.domain.ItineraryDraftFailure

internal data class ItineraryUiState(
    val form: ItineraryFormState = ItineraryFormState(),
    val fieldErrors: ItineraryFieldErrors = ItineraryFieldErrors(),
    val generationState: ItineraryGenerationUiState = ItineraryGenerationUiState.Idle,
    val saveState: ItinerarySaveUiState = ItinerarySaveUiState.Idle,
)

internal data class ItineraryFormState(
    val city: ItineraryCity? = null,
    val localDate: String = "",
    val startLocalTime: String = "",
    val endLocalTime: String = "",
    val maximumStops: String = "",
    val notes: String = "",
)

internal data class ItineraryFieldErrors(
    val city: ItineraryValidationError? = null,
    val localDate: ItineraryValidationError? = null,
    val startLocalTime: ItineraryValidationError? = null,
    val endLocalTime: ItineraryValidationError? = null,
    val maximumStops: ItineraryValidationError? = null,
    val notes: ItineraryValidationError? = null,
) {
    val hasErrors: Boolean
        get() = listOf(
            city,
            localDate,
            startLocalTime,
            endLocalTime,
            maximumStops,
            notes,
        ).any { it != null }
}

internal enum class ItineraryValidationError {
    CITY_REQUIRED,
    DATE_REQUIRED,
    DATE_INVALID,
    START_TIME_REQUIRED,
    START_TIME_INVALID,
    END_TIME_REQUIRED,
    END_TIME_INVALID,
    END_NOT_AFTER_START,
    MAXIMUM_STOPS_REQUIRED,
    MAXIMUM_STOPS_NOT_INTEGER,
    MAXIMUM_STOPS_OUT_OF_RANGE,
    NOTES_TOO_LONG,
}

internal sealed interface ItineraryGenerationUiState {
    data object Idle : ItineraryGenerationUiState

    data object Loading : ItineraryGenerationUiState

    data class Content(
        val draft: ItineraryDraft,
    ) : ItineraryGenerationUiState

    data object Cancelled : ItineraryGenerationUiState

    data class Error(
        val reason: ItineraryDraftFailure,
    ) : ItineraryGenerationUiState

    data object Unavailable : ItineraryGenerationUiState
}

internal sealed interface ItinerarySaveUiState {
    data object Idle : ItinerarySaveUiState

    data object Saving : ItinerarySaveUiState

    data object Saved : ItinerarySaveUiState

    data object PersistenceUnavailable : ItinerarySaveUiState

    data object Failed : ItinerarySaveUiState
}
