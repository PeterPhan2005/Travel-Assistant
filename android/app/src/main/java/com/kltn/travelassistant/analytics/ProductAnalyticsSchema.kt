package com.kltn.travelassistant.analytics

internal enum class ProductAnalyticsEventName(val wireValue: String) {
    NAVIGATION_CONVERSION("navigation_conversion"),
    ITINERARY_CREATION("itinerary_creation"),
    VOICE_INTENT_RESULT("voice_intent_result"),
    TRIP_RETURN("trip_return"),
    GEOCONTEXT_OPENED("geocontext_opened"),
}

internal enum class ProductAnalyticsPropertyKey(val wireValue: String) {
    STAGE("stage"),
    POI_ID("poi_id"),
    OUTCOME("outcome"),
    FAILURE_CATEGORY("failure_category"),
    INTENT("intent"),
    RESULT_STATE("result_state"),
}

internal class ProductAnalyticsProperty(
    val key: ProductAnalyticsPropertyKey,
    val value: String,
)

internal object ProductAnalyticsSchema {
    fun eventName(event: ProductAnalyticsEvent): ProductAnalyticsEventName = when (event) {
        is ProductAnalyticsEvent.NavigationConversion ->
            ProductAnalyticsEventName.NAVIGATION_CONVERSION
        is ProductAnalyticsEvent.ItineraryCreation ->
            ProductAnalyticsEventName.ITINERARY_CREATION
        is ProductAnalyticsEvent.VoiceIntentResult ->
            ProductAnalyticsEventName.VOICE_INTENT_RESULT
        ProductAnalyticsEvent.TripReturn -> ProductAnalyticsEventName.TRIP_RETURN
        is ProductAnalyticsEvent.GeocontextOpened ->
            ProductAnalyticsEventName.GEOCONTEXT_OPENED
    }

    fun properties(event: ProductAnalyticsEvent): List<ProductAnalyticsProperty> = when (event) {
        is ProductAnalyticsEvent.NavigationConversion -> listOf(
            ProductAnalyticsProperty(ProductAnalyticsPropertyKey.STAGE, event.stage.wireValue),
            ProductAnalyticsProperty(ProductAnalyticsPropertyKey.POI_ID, event.poiId),
        )
        is ProductAnalyticsEvent.ItineraryCreation -> listOf(
            ProductAnalyticsProperty(ProductAnalyticsPropertyKey.OUTCOME, event.outcome.wireValue),
            ProductAnalyticsProperty(
                ProductAnalyticsPropertyKey.FAILURE_CATEGORY,
                event.failureCategory.wireValue,
            ),
        )
        is ProductAnalyticsEvent.VoiceIntentResult -> listOf(
            ProductAnalyticsProperty(ProductAnalyticsPropertyKey.INTENT, event.intent.wireValue),
            ProductAnalyticsProperty(ProductAnalyticsPropertyKey.OUTCOME, event.outcome.wireValue),
        )
        ProductAnalyticsEvent.TripReturn -> emptyList()
        is ProductAnalyticsEvent.GeocontextOpened -> listOf(
            ProductAnalyticsProperty(
                ProductAnalyticsPropertyKey.RESULT_STATE,
                event.resultState.wireValue,
            ),
        )
    }
}
