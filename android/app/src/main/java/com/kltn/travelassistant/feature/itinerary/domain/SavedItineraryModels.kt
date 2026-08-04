package com.kltn.travelassistant.feature.itinerary.domain

import kotlinx.coroutines.flow.Flow

internal enum class ItinerarySyncState {
    PENDING,
    SYNCED,
    CONFLICT,
    FAILED,
}

internal data class SavedItinerary(
    val id: String,
    val title: String,
    val draft: ItineraryDraft,
    val syncState: ItinerarySyncState,
)

internal sealed interface SavedItineraryLibraryState {
    data object Loading : SavedItineraryLibraryState

    data object SignedOut : SavedItineraryLibraryState

    data class Content(
        val itineraries: List<SavedItinerary>,
    ) : SavedItineraryLibraryState

    data object Failed : SavedItineraryLibraryState
}

internal sealed interface SavedItineraryDeleteResult {
    data object DeletedLocally : SavedItineraryDeleteResult

    data object AuthenticationRequired : SavedItineraryDeleteResult

    data object NotFound : SavedItineraryDeleteResult

    data object Failed : SavedItineraryDeleteResult
}

internal interface SavedItineraryRepository {
    fun observeLibrary(): Flow<SavedItineraryLibraryState>

    suspend fun delete(itineraryId: String): SavedItineraryDeleteResult
}
