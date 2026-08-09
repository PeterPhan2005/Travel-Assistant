package com.kltn.travelassistant.analytics

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class InMemoryProductAnalyticsTest {
    @Test
    fun detailSessionAndDuplicateNavigationTapsAreCountedOnce() {
        val analytics = InMemoryProductAnalytics(enabled = true)
        val detail = ProductAnalyticsEvent.NavigationConversion(
            NavigationConversionStage.DETAIL_OPENED,
            "poi-1",
        )
        val requested = ProductAnalyticsEvent.NavigationConversion(
            NavigationConversionStage.NAVIGATION_REQUESTED,
            "poi-1",
        )

        analytics.track(requested)
        analytics.track(detail)
        analytics.track(requested)
        analytics.track(requested)

        assertEquals(listOf(detail, requested), analytics.snapshot().map { it.event })
        assertEquals(listOf(1L, 2L), analytics.snapshot().map { it.sequence })
    }

    @Test
    fun reopeningDetailStartsANewConversionSessionWithoutConfigurationDuplicates() {
        val analytics = InMemoryProductAnalytics(enabled = true)
        val detail = ProductAnalyticsEvent.NavigationConversion(
            NavigationConversionStage.DETAIL_OPENED,
            "poi-1",
        )
        val requested = ProductAnalyticsEvent.NavigationConversion(
            NavigationConversionStage.NAVIGATION_REQUESTED,
            "poi-1",
        )

        analytics.track(detail)
        analytics.track(requested)
        analytics.track(requested)
        analytics.track(detail)
        analytics.track(requested)

        assertEquals(
            listOf(detail, requested, detail, requested),
            analytics.snapshot().map { it.event },
        )
    }

    @Test
    fun boundedFifoAndClearAreDeterministic() {
        val analytics = InMemoryProductAnalytics(enabled = true, capacity = 2)

        analytics.track(ProductAnalyticsEvent.TripReturn)
        analytics.track(ProductAnalyticsEvent.GeocontextOpened(GeocontextResultState.EMPTY))
        analytics.track(
            ProductAnalyticsEvent.ItineraryCreation(ItineraryCreationOutcome.ATTEMPTED),
        )

        assertEquals(2, analytics.snapshot().size)
        assertEquals(listOf(2L, 3L), analytics.snapshot().map { it.sequence })
        analytics.clear()
        assertTrue(analytics.snapshot().isEmpty())
        analytics.track(ProductAnalyticsEvent.TripReturn)
        assertEquals(1L, analytics.snapshot().single().sequence)
    }

    @Test
    fun disabledRuntimeIsAReleaseNoOp() {
        val analytics = InMemoryProductAnalytics(enabled = false)

        analytics.track(ProductAnalyticsEvent.TripReturn)

        assertTrue(analytics.snapshot().isEmpty())
    }
}
