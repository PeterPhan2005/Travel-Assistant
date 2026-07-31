package com.kltn.travelassistant.feature.itinerary.presentation

import com.kltn.travelassistant.feature.itinerary.domain.ItineraryCity
import com.kltn.travelassistant.feature.itinerary.domain.ItineraryLocationSnapshot
import com.kltn.travelassistant.feature.itinerary.domain.MAX_ITINERARY_NOTES_CODE_POINTS
import java.time.LocalDate
import java.time.LocalTime
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class ItineraryFormValidatorTest {
    @Test
    fun initialStateReportsEveryRequiredFieldWithoutInventingDefaults() {
        val result = validateItineraryForm(ItineraryFormState(), null) as
            ItineraryFormValidationResult.Invalid

        assertEquals(ItineraryValidationError.CITY_REQUIRED, result.errors.city)
        assertEquals(ItineraryValidationError.DATE_REQUIRED, result.errors.localDate)
        assertEquals(
            ItineraryValidationError.START_TIME_REQUIRED,
            result.errors.startLocalTime,
        )
        assertEquals(
            ItineraryValidationError.END_TIME_REQUIRED,
            result.errors.endLocalTime,
        )
        assertEquals(
            ItineraryValidationError.MAXIMUM_STOPS_REQUIRED,
            result.errors.maximumStops,
        )
    }

    @Test
    fun missingCityFailsWhileOtherwiseValidValuesRemainUntouched() {
        val result = validateItineraryForm(validForm().copy(city = null), null) as
            ItineraryFormValidationResult.Invalid

        assertEquals(ItineraryValidationError.CITY_REQUIRED, result.errors.city)
        assertNull(result.errors.localDate)
        assertNull(result.errors.startLocalTime)
    }

    @Test
    fun invalidCalendarDateFailsAndPastDateIsNotRejected() {
        val invalid = validateItineraryForm(
            validForm().copy(localDate = "2026-02-30"),
            null,
        ) as ItineraryFormValidationResult.Invalid
        assertEquals(ItineraryValidationError.DATE_INVALID, invalid.errors.localDate)

        val past = validateItineraryForm(
            validForm().copy(localDate = "2020-01-01"),
            null,
        ) as ItineraryFormValidationResult.Valid
        assertEquals(LocalDate.of(2020, 1, 1), past.request.localDate)
    }

    @Test
    fun invalidStartAndEndFormatsFailLocally() {
        val result = validateItineraryForm(
            validForm().copy(
                startLocalTime = "9:00",
                endLocalTime = "25:00",
            ),
            null,
        ) as ItineraryFormValidationResult.Invalid

        assertEquals(
            ItineraryValidationError.START_TIME_INVALID,
            result.errors.startLocalTime,
        )
        assertEquals(
            ItineraryValidationError.END_TIME_INVALID,
            result.errors.endLocalTime,
        )
    }

    @Test
    fun equalOrReversedWindowFailsWithoutSwappingValues() {
        listOf("09:00", "08:59").forEach { end ->
            val result = validateItineraryForm(
                validForm().copy(endLocalTime = end),
                null,
            ) as ItineraryFormValidationResult.Invalid

            assertEquals(
                ItineraryValidationError.END_NOT_AFTER_START,
                result.errors.endLocalTime,
            )
        }
    }

    @Test
    fun maximumStopsRejectsBelowAboveAndNonIntegerWithoutClamping() {
        mapOf(
            "0" to ItineraryValidationError.MAXIMUM_STOPS_OUT_OF_RANGE,
            "21" to ItineraryValidationError.MAXIMUM_STOPS_OUT_OF_RANGE,
            "2.5" to ItineraryValidationError.MAXIMUM_STOPS_NOT_INTEGER,
        ).forEach { (value, expected) ->
            val result = validateItineraryForm(
                validForm().copy(maximumStops = value),
                null,
            ) as ItineraryFormValidationResult.Invalid
            assertEquals(expected, result.errors.maximumStops)
        }
    }

    @Test
    fun overLimitNotesFailWithoutTruncation() {
        val notes = "a".repeat(MAX_ITINERARY_NOTES_CODE_POINTS + 1)
        val result = validateItineraryForm(
            validForm().copy(notes = notes),
            null,
        ) as ItineraryFormValidationResult.Invalid

        assertEquals(ItineraryValidationError.NOTES_TOO_LONG, result.errors.notes)
    }

    @Test
    fun hcmcMapsEveryApprovedFieldExactly() {
        val form = validForm().copy(notes = "Đi bộ ít")
        val result = validateItineraryForm(form, null) as
            ItineraryFormValidationResult.Valid

        assertEquals(ItineraryCity.HO_CHI_MINH_CITY, result.request.city)
        assertEquals("Asia/Ho_Chi_Minh", result.request.timezone)
        assertEquals(LocalDate.of(2026, 8, 1), result.request.localDate)
        assertEquals(LocalTime.of(9, 0), result.request.startLocalTime)
        assertEquals(LocalTime.of(17, 0), result.request.endLocalTime)
        assertEquals(4, result.request.maximumStops)
        assertEquals("Đi bộ ít", result.request.notes)
        assertNull(result.request.currentLocation)
    }

    @Test
    fun bangkokUsesClosedTimezoneMappingAndOptionalMemoryLocation() {
        val location = ItineraryLocationSnapshot(13.7563, 100.5018)
        val result = validateItineraryForm(
            validForm().copy(city = ItineraryCity.BANGKOK),
            location,
        ) as ItineraryFormValidationResult.Valid

        assertEquals("Asia/Bangkok", result.request.timezone)
        assertEquals(location, result.request.currentLocation)
    }

    @Test
    fun unicodeNotesBoundCountsCodePointsRatherThanUtf16Units() {
        val notes = "😀".repeat(MAX_ITINERARY_NOTES_CODE_POINTS)
        val result = validateItineraryForm(
            validForm().copy(notes = notes),
            null,
        )

        assertTrue(result is ItineraryFormValidationResult.Valid)
    }

    private fun validForm() = ItineraryFormState(
        city = ItineraryCity.HO_CHI_MINH_CITY,
        localDate = "2026-08-01",
        startLocalTime = "09:00",
        endLocalTime = "17:00",
        maximumStops = "4",
    )
}
