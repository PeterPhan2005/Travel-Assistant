package com.kltn.travelassistant.feature.itinerary.domain

import java.time.LocalDate
import java.time.LocalTime
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class ItineraryDraftValidationTest {
    @Test
    fun chronologicalNonOverlappingItemsAreAcceptedWithoutReordering() {
        val draft = validDraft()

        assertTrue(isValidDraftForRequest(draft, request()))
        assertEquals(
            listOf("Bưu điện", "Bảo tàng"),
            draft.items.map(ItineraryDraftItem::title),
        )
    }

    @Test
    fun emptyItemsAreRejected() {
        assertFalse(
            isValidDraftForRequest(validDraft().copy(items = emptyList()), request()),
        )
    }

    @Test
    fun overlappingOrNonChronologicalItemsAreRejected() {
        val overlapping = validDraft().copy(
            items = listOf(
                item("Bưu điện", 9, 0, 12, 0),
                item("Bảo tàng", 11, 30, 17, 0),
            ),
        )
        val reversed = validDraft().copy(items = validDraft().items.reversed())

        assertFalse(isValidDraftForRequest(overlapping, request()))
        assertFalse(isValidDraftForRequest(reversed, request()))
    }

    @Test
    fun itemOutsideRequestedWindowIsRejected() {
        val outside = validDraft().copy(
            items = listOf(item("Quá sớm", 8, 59, 10, 0)),
        )

        assertFalse(isValidDraftForRequest(outside, request()))
    }

    @Test
    fun invalidItemIntervalIsRejected() {
        val invalid = validDraft().copy(
            items = listOf(item("Không hợp lệ", 10, 0, 10, 0)),
        )

        assertFalse(isValidDraftForRequest(invalid, request()))
    }

    @Test
    fun stopCountAboveRequestMaximumIsRejected() {
        val oneStopRequest = request().copy(maximumStops = 1)

        assertFalse(isValidDraftForRequest(validDraft(), oneStopRequest))
    }

    @Test
    fun exactWindowCityDateAndTimezoneMustMatch() {
        assertFalse(
            isValidDraftForRequest(
                validDraft().copy(timezone = "Asia/Bangkok"),
                request(),
            ),
        )
        assertFalse(
            isValidDraftForRequest(
                validDraft().copy(city = ItineraryCity.BANGKOK),
                request(),
            ),
        )
    }

    @Test
    fun assumptionsAndWarningsArePreservedAndUnsafeTextFailsClosed() {
        val draft = validDraft().copy(
            assumptions = listOf("Giả định rõ ràng"),
            warnings = listOf(ItineraryDraftWarning("Cảnh báo an toàn")),
        )
        assertTrue(isValidDraftForRequest(draft, request()))
        assertEquals("Giả định rõ ràng", draft.assumptions.single())
        assertEquals("Cảnh báo an toàn", draft.warnings.single().message)

        assertFalse(
            isValidDraftForRequest(
                draft.copy(warnings = listOf(ItineraryDraftWarning("raw\ninternal"))),
                request(),
            ),
        )
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

    private fun validDraft() = ItineraryDraft(
        city = ItineraryCity.HO_CHI_MINH_CITY,
        localDate = LocalDate.of(2026, 8, 1),
        timezone = "Asia/Ho_Chi_Minh",
        startLocalTime = LocalTime.of(9, 0),
        endLocalTime = LocalTime.of(17, 0),
        items = listOf(
            item("Bưu điện", 9, 0, 13, 0),
            item("Bảo tàng", 13, 0, 17, 0),
        ),
        assumptions = listOf("Chưa tính thời gian di chuyển."),
        warnings = listOf(ItineraryDraftWarning("Hãy kiểm tra giờ mở cửa.")),
    )

    private fun item(
        title: String,
        startHour: Int,
        startMinute: Int,
        endHour: Int,
        endMinute: Int,
    ) = ItineraryDraftItem(
        title = title,
        startLocalTime = LocalTime.of(startHour, startMinute),
        endLocalTime = LocalTime.of(endHour, endMinute),
    )
}
