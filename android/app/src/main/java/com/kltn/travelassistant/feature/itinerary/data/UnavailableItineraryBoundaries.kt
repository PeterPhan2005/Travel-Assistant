package com.kltn.travelassistant.feature.itinerary.data

import com.kltn.travelassistant.feature.itinerary.domain.ItineraryDraft
import com.kltn.travelassistant.feature.itinerary.domain.ItinerarySaveBoundary
import com.kltn.travelassistant.feature.itinerary.domain.ItinerarySaveResult
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
internal class UnavailableItinerarySaveBoundary @Inject constructor() :
    ItinerarySaveBoundary {
    override suspend fun save(draft: ItineraryDraft): ItinerarySaveResult =
        ItinerarySaveResult.PersistenceUnavailable
}
