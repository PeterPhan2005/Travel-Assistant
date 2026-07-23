package com.kltn.travelassistant.navigation.external

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
