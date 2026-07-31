package com.kltn.travelassistant.feature.itinerary.domain

import java.time.LocalDate
import java.time.LocalTime

internal const val MAX_ITINERARY_NOTES_CODE_POINTS = 500

internal enum class ItineraryCity(
    val timezone: String,
) {
    HO_CHI_MINH_CITY("Asia/Ho_Chi_Minh"),
    BANGKOK("Asia/Bangkok"),
}

internal data class ItineraryLocationSnapshot(
    val latitude: Double,
    val longitude: Double,
) {
    init {
        require(latitude.isFinite() && latitude in -90.0..90.0)
        require(longitude.isFinite() && longitude in -180.0..180.0)
    }
}

internal data class ItineraryDraftRequest(
    val city: ItineraryCity,
    val localDate: LocalDate,
    val timezone: String,
    val startLocalTime: LocalTime,
    val endLocalTime: LocalTime,
    val maximumStops: Int,
    val notes: String?,
    val currentLocation: ItineraryLocationSnapshot?,
)

internal data class ItineraryDraftItem(
    val title: String,
    val startLocalTime: LocalTime,
    val endLocalTime: LocalTime,
)

internal data class ItineraryDraftWarning(
    val message: String,
)

internal data class ItineraryDraft(
    val city: ItineraryCity,
    val localDate: LocalDate,
    val timezone: String,
    val startLocalTime: LocalTime,
    val endLocalTime: LocalTime,
    val items: List<ItineraryDraftItem>,
    val assumptions: List<String>,
    val warnings: List<ItineraryDraftWarning>,
)

internal fun isValidDraftForRequest(
    draft: ItineraryDraft,
    request: ItineraryDraftRequest,
): Boolean {
    if (
        draft.city != request.city ||
        draft.localDate != request.localDate ||
        draft.timezone != request.timezone ||
        draft.startLocalTime != request.startLocalTime ||
        draft.endLocalTime != request.endLocalTime ||
        draft.items.isEmpty() ||
        draft.items.size > request.maximumStops ||
        draft.assumptions.isEmpty()
    ) {
        return false
    }
    if (
        draft.assumptions.any { !it.isSafePresentationText(maximumLength = 240) } ||
        draft.warnings.any { !it.message.isSafePresentationText(maximumLength = 240) }
    ) {
        return false
    }
    var previousEnd = request.startLocalTime
    for (item in draft.items) {
        if (
            !item.title.isSafePresentationText(maximumLength = 240) ||
            item.startLocalTime >= item.endLocalTime ||
            item.startLocalTime < request.startLocalTime ||
            item.endLocalTime > request.endLocalTime ||
            item.startLocalTime < previousEnd
        ) {
            return false
        }
        previousEnd = item.endLocalTime
    }
    return true
}

private fun String.isSafePresentationText(maximumLength: Int): Boolean =
    isNotBlank() &&
        length <= maximumLength &&
        none(Char::isISOControl)
