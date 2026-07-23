package com.kltn.travelassistant.navigation.external

import com.kltn.travelassistant.feature.poi.domain.PoiNavigationTarget

interface ExternalNavigationLauncher {
    fun open(target: PoiNavigationTarget): ExternalNavigationResult
}

sealed interface ExternalNavigationResult {
    data object Opened : ExternalNavigationResult

    data object NoCompatibleApplication : ExternalNavigationResult

    data object InvalidDestination : ExternalNavigationResult

    data object LaunchFailed : ExternalNavigationResult
}

internal fun PoiNavigationTarget.isValidForExternalNavigation(): Boolean =
    poiId.isNotBlank() &&
        displayName.isNotBlank() &&
        latitude.isFinite() &&
        longitude.isFinite() &&
        latitude in -90.0..90.0 &&
        longitude in -180.0..180.0
