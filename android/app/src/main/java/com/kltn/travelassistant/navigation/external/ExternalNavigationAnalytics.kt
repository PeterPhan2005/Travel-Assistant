package com.kltn.travelassistant.navigation.external

import com.kltn.travelassistant.analytics.NavigationConversionStage
import com.kltn.travelassistant.analytics.ProductAnalytics
import com.kltn.travelassistant.analytics.trackNavigationConversionSafely
import javax.inject.Inject

interface ExternalNavigationAnalytics {
    fun track(event: ExternalNavigationAnalyticsEvent)
}

sealed interface ExternalNavigationAnalyticsEvent {
    val poiId: String

    data class Requested(override val poiId: String) : ExternalNavigationAnalyticsEvent

    data class Opened(override val poiId: String) : ExternalNavigationAnalyticsEvent

    data class Unavailable(override val poiId: String) : ExternalNavigationAnalyticsEvent

    data class InvalidDestination(override val poiId: String) : ExternalNavigationAnalyticsEvent

    data class LaunchFailed(override val poiId: String) : ExternalNavigationAnalyticsEvent
}

class NoOpExternalNavigationAnalytics @Inject constructor() : ExternalNavigationAnalytics {
    override fun track(event: ExternalNavigationAnalyticsEvent) = Unit
}

class ProductExternalNavigationAnalytics @Inject constructor(
    private val productAnalytics: ProductAnalytics,
) : ExternalNavigationAnalytics {
    override fun track(event: ExternalNavigationAnalyticsEvent) {
        if (event !is ExternalNavigationAnalyticsEvent.Requested) return
        productAnalytics.trackNavigationConversionSafely(
            stage = NavigationConversionStage.NAVIGATION_REQUESTED,
            poiId = event.poiId,
        )
    }
}
