package com.kltn.travelassistant.analytics

const val PRODUCT_ANALYTICS_SCHEMA_VERSION = 1

interface ProductAnalytics {
    fun track(event: ProductAnalyticsEvent)
}

sealed interface ProductAnalyticsEvent {
    data class NavigationConversion(
        val stage: NavigationConversionStage,
        val poiId: String,
    ) : ProductAnalyticsEvent {
        init {
            require(poiId.isSafeAnalyticsPoiId())
        }
    }

    data class ItineraryCreation(
        val outcome: ItineraryCreationOutcome,
        val failureCategory: ItineraryFailureCategory = ItineraryFailureCategory.NONE,
    ) : ProductAnalyticsEvent {
        init {
            require(
                (outcome == ItineraryCreationOutcome.FAILED) ==
                    (failureCategory != ItineraryFailureCategory.NONE),
            )
        }
    }

    data class VoiceIntentResult(
        val intent: AnalyticsAssistantIntent,
        val outcome: VoiceIntentOutcome,
    ) : ProductAnalyticsEvent

    data object TripReturn : ProductAnalyticsEvent

    data class GeocontextOpened(
        val resultState: GeocontextResultState,
    ) : ProductAnalyticsEvent
}

enum class NavigationConversionStage(internal val wireValue: String) {
    DETAIL_OPENED("detail_opened"),
    NAVIGATION_REQUESTED("navigation_requested"),
}

enum class ItineraryCreationOutcome(internal val wireValue: String) {
    ATTEMPTED("attempted"),
    SUCCEEDED("succeeded"),
    CANCELLED("cancelled"),
    FAILED("failed"),
}

enum class ItineraryFailureCategory(internal val wireValue: String) {
    NONE("none"),
    OFFLINE("offline"),
    AUTHENTICATION_REQUIRED("authentication_required"),
    INVALID_REQUEST("invalid_request"),
    TIMEOUT("timeout"),
    RATE_LIMITED("rate_limited"),
    UNAVAILABLE("unavailable"),
    INVALID_RESPONSE("invalid_response"),
    UNSUPPORTED_TRANSPORT("unsupported_transport"),
}

enum class AnalyticsAssistantIntent(internal val wireValue: String) {
    NEARBY_DISCOVERY("nearby_discovery"),
    POI_INFORMATION("poi_information"),
    LOCAL_CULTURE("local_culture"),
    ITINERARY_DRAFTING("itinerary_drafting"),
    GENERAL_TRAVEL_HELP("general_travel_help"),
    UNSUPPORTED("unsupported"),
}

enum class VoiceIntentOutcome(internal val wireValue: String) {
    SUCCESS("success"),
    PARTIAL("partial"),
    FAILED("failed"),
}

enum class GeocontextResultState(internal val wireValue: String) {
    CONTENT("content"),
    EMPTY("empty"),
}

object NoOpProductAnalytics : ProductAnalytics {
    override fun track(event: ProductAnalyticsEvent) = Unit
}

fun ProductAnalytics.trackSafely(event: ProductAnalyticsEvent) {
    try {
        track(event)
    } catch (_: RuntimeException) {
        // Product behavior must not depend on analytics delivery.
    }
}

fun ProductAnalytics.trackNavigationConversionSafely(
    stage: NavigationConversionStage,
    poiId: String,
) {
    try {
        track(ProductAnalyticsEvent.NavigationConversion(stage, poiId))
    } catch (_: RuntimeException) {
        // Invalid product data or analytics delivery must not block the UI action.
    }
}

private fun String.isSafeAnalyticsPoiId(): Boolean =
    isNotBlank() && length <= 160 && none(Char::isISOControl)
