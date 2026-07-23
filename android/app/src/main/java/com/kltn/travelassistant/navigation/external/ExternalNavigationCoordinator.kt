package com.kltn.travelassistant.navigation.external

import com.kltn.travelassistant.feature.poi.domain.PoiNavigationTarget
import javax.inject.Inject

class ExternalNavigationCoordinator @Inject constructor(
    private val launcher: ExternalNavigationLauncher,
    private val analytics: ExternalNavigationAnalytics,
) {
    fun open(target: PoiNavigationTarget): ExternalNavigationResult {
        trackSafely(ExternalNavigationAnalyticsEvent.Requested(target.poiId))
        val result = try {
            launcher.open(target)
        } catch (_: RuntimeException) {
            ExternalNavigationResult.LaunchFailed
        }
        trackSafely(result.toAnalyticsEvent(target.poiId))
        return result
    }

    private fun trackSafely(event: ExternalNavigationAnalyticsEvent) {
        try {
            analytics.track(event)
        } catch (_: RuntimeException) {
            // Analytics must never block or change external navigation behavior.
        }
    }

    private fun ExternalNavigationResult.toAnalyticsEvent(
        poiId: String,
    ): ExternalNavigationAnalyticsEvent = when (this) {
        ExternalNavigationResult.Opened -> ExternalNavigationAnalyticsEvent.Opened(poiId)
        ExternalNavigationResult.NoCompatibleApplication ->
            ExternalNavigationAnalyticsEvent.Unavailable(poiId)
        ExternalNavigationResult.InvalidDestination ->
            ExternalNavigationAnalyticsEvent.InvalidDestination(poiId)
        ExternalNavigationResult.LaunchFailed ->
            ExternalNavigationAnalyticsEvent.LaunchFailed(poiId)
    }
}
