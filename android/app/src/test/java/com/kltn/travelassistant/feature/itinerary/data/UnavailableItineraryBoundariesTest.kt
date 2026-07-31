package com.kltn.travelassistant.feature.itinerary.data

import com.kltn.travelassistant.feature.itinerary.domain.ItineraryCity
import com.kltn.travelassistant.feature.itinerary.domain.ItineraryDraft
import com.kltn.travelassistant.feature.itinerary.domain.ItineraryDraftFailure
import com.kltn.travelassistant.feature.itinerary.domain.ItineraryDraftGenerationResult
import com.kltn.travelassistant.feature.itinerary.domain.ItineraryDraftRequest
import com.kltn.travelassistant.feature.itinerary.domain.ItinerarySaveResult
import java.time.LocalDate
import java.time.LocalTime
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Test

class UnavailableItineraryBoundariesTest {
    @Test
    fun productionGeneratorReportsUnsupportedTransportWithoutFabricatingDraft() = runTest {
        val result = UnsupportedTransportItineraryDraftGenerator().generate(request())

        assertEquals(
            ItineraryDraftGenerationResult.Failure(
                ItineraryDraftFailure.UNSUPPORTED_TRANSPORT,
            ),
            result,
        )
    }

    @Test
    fun productionSaveBoundaryReportsThatNothingWasPersisted() = runTest {
        val result = UnavailableItinerarySaveBoundary().save(
            ItineraryDraft(
                city = ItineraryCity.HO_CHI_MINH_CITY,
                localDate = LocalDate.of(2026, 8, 1),
                timezone = "Asia/Ho_Chi_Minh",
                startLocalTime = LocalTime.of(9, 0),
                endLocalTime = LocalTime.of(17, 0),
                items = emptyList(),
                assumptions = emptyList(),
                warnings = emptyList(),
            ),
        )

        assertEquals(ItinerarySaveResult.PersistenceUnavailable, result)
    }

    private fun request() = ItineraryDraftRequest(
        city = ItineraryCity.HO_CHI_MINH_CITY,
        localDate = LocalDate.of(2026, 8, 1),
        timezone = "Asia/Ho_Chi_Minh",
        startLocalTime = LocalTime.of(9, 0),
        endLocalTime = LocalTime.of(17, 0),
        maximumStops = 4,
        notes = null,
        currentLocation = null,
    )
}
