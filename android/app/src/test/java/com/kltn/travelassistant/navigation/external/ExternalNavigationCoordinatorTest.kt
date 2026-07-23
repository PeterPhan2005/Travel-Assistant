package com.kltn.travelassistant.navigation.external

import com.kltn.travelassistant.feature.poi.domain.PoiNavigationTarget
import org.junit.Assert.assertEquals
import org.junit.Test

class ExternalNavigationCoordinatorTest {
    @Test
    fun tracksRequestAndTypedOutcomeWithoutLocationData() {
        val cases = listOf(
            ExternalNavigationResult.Opened to ExternalNavigationAnalyticsEvent.Opened(POI_ID),
            ExternalNavigationResult.NoCompatibleApplication to
                ExternalNavigationAnalyticsEvent.Unavailable(POI_ID),
            ExternalNavigationResult.InvalidDestination to
                ExternalNavigationAnalyticsEvent.InvalidDestination(POI_ID),
            ExternalNavigationResult.LaunchFailed to
                ExternalNavigationAnalyticsEvent.LaunchFailed(POI_ID),
        )

        cases.forEach { (launcherResult, expectedOutcome) ->
            val analytics = RecordingAnalytics()
            val coordinator = ExternalNavigationCoordinator(
                launcher = FakeLauncher { launcherResult },
                analytics = analytics,
            )

            assertEquals(launcherResult, coordinator.open(target))
            assertEquals(
                listOf(
                    ExternalNavigationAnalyticsEvent.Requested(POI_ID),
                    expectedOutcome,
                ),
                analytics.events,
            )
        }
    }

    @Test
    fun unexpectedLauncherFailureBecomesControlledFailureAndIsTracked() {
        val analytics = RecordingAnalytics()
        val coordinator = ExternalNavigationCoordinator(
            launcher = FakeLauncher { throw IllegalStateException("Expected test failure") },
            analytics = analytics,
        )

        assertEquals(ExternalNavigationResult.LaunchFailed, coordinator.open(target))
        assertEquals(
            listOf(
                ExternalNavigationAnalyticsEvent.Requested(POI_ID),
                ExternalNavigationAnalyticsEvent.LaunchFailed(POI_ID),
            ),
            analytics.events,
        )
    }

    @Test
    fun analyticsFailureDoesNotBlockLaunch() {
        val coordinator = ExternalNavigationCoordinator(
            launcher = FakeLauncher { ExternalNavigationResult.Opened },
            analytics = object : ExternalNavigationAnalytics {
                override fun track(event: ExternalNavigationAnalyticsEvent) {
                    throw IllegalStateException("Expected test failure")
                }
            },
        )

        assertEquals(ExternalNavigationResult.Opened, coordinator.open(target))
    }

    private class FakeLauncher(
        private val result: () -> ExternalNavigationResult,
    ) : ExternalNavigationLauncher {
        override fun open(target: PoiNavigationTarget): ExternalNavigationResult = result()
    }

    private class RecordingAnalytics : ExternalNavigationAnalytics {
        val events = mutableListOf<ExternalNavigationAnalyticsEvent>()

        override fun track(event: ExternalNavigationAnalyticsEvent) {
            events += event
        }
    }

    private companion object {
        const val POI_ID = "ben-thanh"
        val target = PoiNavigationTarget(
            poiId = POI_ID,
            displayName = "Chợ Bến Thành",
            latitude = 10.7725,
            longitude = 106.6980,
        )
    }
}
