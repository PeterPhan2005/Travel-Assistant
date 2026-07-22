package com.kltn.travelassistant.feature.home.presentation

import com.kltn.travelassistant.data.location.DeviceLocation
import com.kltn.travelassistant.feature.nearby.domain.NearbyPoi

data class HomeUiState(
    val appName: String = "",
    val locationState: LocationUiState = LocationUiState.Idle,
    val nearbyQuery: String = "",
    val nearbySearchState: NearbySearchUiState = NearbySearchUiState.WaitingForLocation,
)

sealed interface NearbySearchUiState {
    data object WaitingForLocation : NearbySearchUiState

    data object Loading : NearbySearchUiState

    data class Content(val results: List<NearbyPoi>) : NearbySearchUiState

    data object Empty : NearbySearchUiState

    data object Error : NearbySearchUiState
}

sealed interface LocationUiState {
    data object Idle : LocationUiState

    data object Loading : LocationUiState

    data class Available(val location: DeviceLocation) : LocationUiState

    data class PermissionDenied(
        val canRequestPermissionAgain: Boolean,
    ) : LocationUiState

    data class Error(val reason: LocationError) : LocationUiState
}

enum class LocationError {
    PROVIDER_UNAVAILABLE,
    TIMEOUT,
    CANCELLED,
    FAILED,
}
