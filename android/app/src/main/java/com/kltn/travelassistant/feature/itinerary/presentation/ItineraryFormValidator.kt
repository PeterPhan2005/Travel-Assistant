package com.kltn.travelassistant.feature.itinerary.presentation

import com.kltn.travelassistant.feature.itinerary.domain.ItineraryCity
import com.kltn.travelassistant.feature.itinerary.domain.ItineraryDraftRequest
import com.kltn.travelassistant.feature.itinerary.domain.ItineraryLocationSnapshot
import com.kltn.travelassistant.feature.itinerary.domain.MAX_ITINERARY_NOTES_CODE_POINTS
import java.time.DateTimeException
import java.time.LocalDate
import java.time.LocalTime

internal sealed interface ItineraryFormValidationResult {
    data class Valid(
        val request: ItineraryDraftRequest,
    ) : ItineraryFormValidationResult

    data class Invalid(
        val errors: ItineraryFieldErrors,
    ) : ItineraryFormValidationResult
}

internal fun validateItineraryForm(
    form: ItineraryFormState,
    currentLocation: ItineraryLocationSnapshot?,
): ItineraryFormValidationResult {
    val cityError = if (form.city == null) {
        ItineraryValidationError.CITY_REQUIRED
    } else {
        null
    }
    val localDate = parseLocalDate(form.localDate)
    val dateError = when {
        form.localDate.isBlank() -> ItineraryValidationError.DATE_REQUIRED
        localDate == null -> ItineraryValidationError.DATE_INVALID
        else -> null
    }
    val start = parseLocalTime(form.startLocalTime)
    val startError = when {
        form.startLocalTime.isBlank() -> ItineraryValidationError.START_TIME_REQUIRED
        start == null -> ItineraryValidationError.START_TIME_INVALID
        else -> null
    }
    val end = parseLocalTime(form.endLocalTime)
    var endError = when {
        form.endLocalTime.isBlank() -> ItineraryValidationError.END_TIME_REQUIRED
        end == null -> ItineraryValidationError.END_TIME_INVALID
        else -> null
    }
    if (start != null && end != null && start >= end) {
        endError = ItineraryValidationError.END_NOT_AFTER_START
    }
    val maximumStops = form.maximumStops.toIntOrNull()
    val maximumStopsError = when {
        form.maximumStops.isBlank() -> ItineraryValidationError.MAXIMUM_STOPS_REQUIRED
        maximumStops == null -> ItineraryValidationError.MAXIMUM_STOPS_NOT_INTEGER
        maximumStops !in 1..20 -> ItineraryValidationError.MAXIMUM_STOPS_OUT_OF_RANGE
        else -> null
    }
    val notesError = if (
        form.notes.codePointCount(0, form.notes.length) >
        MAX_ITINERARY_NOTES_CODE_POINTS
    ) {
        ItineraryValidationError.NOTES_TOO_LONG
    } else {
        null
    }
    val errors = ItineraryFieldErrors(
        city = cityError,
        localDate = dateError,
        startLocalTime = startError,
        endLocalTime = endError,
        maximumStops = maximumStopsError,
        notes = notesError,
    )
    if (errors.hasErrors) {
        return ItineraryFormValidationResult.Invalid(errors)
    }
    val city = form.city ?: return ItineraryFormValidationResult.Invalid(
        ItineraryFieldErrors(city = ItineraryValidationError.CITY_REQUIRED),
    )
    return ItineraryFormValidationResult.Valid(
        ItineraryDraftRequest(
            city = city,
            localDate = requireNotNull(localDate),
            timezone = itineraryTimezone(city),
            startLocalTime = requireNotNull(start),
            endLocalTime = requireNotNull(end),
            maximumStops = requireNotNull(maximumStops),
            notes = form.notes.takeUnless(String::isBlank),
            currentLocation = currentLocation,
        ),
    )
}

internal fun itineraryTimezone(city: ItineraryCity): String = when (city) {
    ItineraryCity.HO_CHI_MINH_CITY -> "Asia/Ho_Chi_Minh"
    ItineraryCity.BANGKOK -> "Asia/Bangkok"
}

private fun parseLocalDate(value: String): LocalDate? {
    if (!value.matches(Regex("""\d{4}-\d{2}-\d{2}"""))) return null
    return try {
        LocalDate.parse(value)
    } catch (_: DateTimeException) {
        null
    }
}

private fun parseLocalTime(value: String): LocalTime? {
    if (!value.matches(Regex("""\d{2}:\d{2}"""))) return null
    return try {
        LocalTime.parse(value)
    } catch (_: DateTimeException) {
        null
    }
}
