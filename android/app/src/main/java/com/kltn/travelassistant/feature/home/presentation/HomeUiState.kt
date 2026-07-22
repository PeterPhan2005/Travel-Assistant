package com.kltn.travelassistant.feature.home.presentation

import com.kltn.travelassistant.data.location.DeviceLocation

data class HomeUiState(
    val appName: String = "",
    val locationState: LocationUiState = LocationUiState.Idle,
)

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
