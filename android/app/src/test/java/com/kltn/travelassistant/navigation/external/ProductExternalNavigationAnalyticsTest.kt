package com.kltn.travelassistant.navigation.external

import com.kltn.travelassistant.analytics.NavigationConversionStage
import com.kltn.travelassistant.analytics.ProductAnalytics
import com.kltn.travelassistant.analytics.ProductAnalyticsEvent
import org.junit.Assert.assertEquals
import org.junit.Test

class ProductExternalNavigationAnalyticsTest {
    @Test
    fun onlyExplicitNavigationRequestMapsToConversionEvent() {
        val productAnalytics = RecordingProductAnalytics()
        val analytics = ProductExternalNavigationAnalytics(productAnalytics)

        analytics.track(ExternalNavigationAnalyticsEvent.Requested("poi-1"))
        analytics.track(ExternalNavigationAnalyticsEvent.Opened("poi-1"))
        analytics.track(ExternalNavigationAnalyticsEvent.Unavailable("poi-1"))
        analytics.track(ExternalNavigationAnalyticsEvent.InvalidDestination("poi-1"))
        analytics.track(ExternalNavigationAnalyticsEvent.LaunchFailed("poi-1"))

        assertEquals(
            listOf(
                ProductAnalyticsEvent.NavigationConversion(
                    NavigationConversionStage.NAVIGATION_REQUESTED,
                    "poi-1",
                ),
            ),
            productAnalytics.events,
        )
    }

    private class RecordingProductAnalytics : ProductAnalytics {
        val events = mutableListOf<ProductAnalyticsEvent>()

        override fun track(event: ProductAnalyticsEvent) {
            events += event
        }
    }
}
