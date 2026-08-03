package com.kltn.travelassistant.feature.itinerary.data

import com.kltn.travelassistant.feature.itinerary.domain.ItineraryCity
import com.kltn.travelassistant.feature.itinerary.domain.ItineraryDraft
import com.kltn.travelassistant.feature.itinerary.domain.ItinerarySaveResult
import java.time.LocalDate
import java.time.LocalTime
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Test

class UnavailableItineraryBoundariesTest {
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
}
