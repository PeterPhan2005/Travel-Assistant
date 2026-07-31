package com.kltn.travelassistant.feature.itinerary.data

import com.kltn.travelassistant.feature.itinerary.domain.ItineraryDraft
import com.kltn.travelassistant.feature.itinerary.domain.ItineraryDraftFailure
import com.kltn.travelassistant.feature.itinerary.domain.ItineraryDraftGenerationResult
import com.kltn.travelassistant.feature.itinerary.domain.ItineraryDraftGenerator
import com.kltn.travelassistant.feature.itinerary.domain.ItineraryDraftRequest
import com.kltn.travelassistant.feature.itinerary.domain.ItinerarySaveBoundary
import com.kltn.travelassistant.feature.itinerary.domain.ItinerarySaveResult
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
internal class UnsupportedTransportItineraryDraftGenerator @Inject constructor() :
    ItineraryDraftGenerator {
    override suspend fun generate(
        request: ItineraryDraftRequest,
    ): ItineraryDraftGenerationResult =
        ItineraryDraftGenerationResult.Failure(
            ItineraryDraftFailure.UNSUPPORTED_TRANSPORT,
        )
}

@Singleton
internal class UnavailableItinerarySaveBoundary @Inject constructor() :
    ItinerarySaveBoundary {
    override suspend fun save(draft: ItineraryDraft): ItinerarySaveResult =
        ItinerarySaveResult.PersistenceUnavailable
}
