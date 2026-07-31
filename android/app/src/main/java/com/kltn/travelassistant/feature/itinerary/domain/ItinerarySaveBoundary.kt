package com.kltn.travelassistant.feature.itinerary.domain

internal interface ItinerarySaveBoundary {
    suspend fun save(draft: ItineraryDraft): ItinerarySaveResult
}

internal sealed interface ItinerarySaveResult {
    data object Saved : ItinerarySaveResult

    data object PersistenceUnavailable : ItinerarySaveResult

    data object Failed : ItinerarySaveResult
}
