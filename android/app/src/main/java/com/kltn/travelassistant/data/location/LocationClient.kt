package com.kltn.travelassistant.data.location

interface LocationClient {
    suspend fun getCurrentLocation(): LocationAcquisitionResult
}

sealed interface LocationAcquisitionResult {
    data class Success(val location: DeviceLocation) : LocationAcquisitionResult

    data object PermissionDenied : LocationAcquisitionResult

    data object ProviderUnavailable : LocationAcquisitionResult

    data object Timeout : LocationAcquisitionResult

    data object Failure : LocationAcquisitionResult
}
