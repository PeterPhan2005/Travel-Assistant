package com.kltn.travelassistant.data.location

data class DeviceLocation(
    val latitude: Double,
    val longitude: Double,
    val accuracyMeters: Float?,
    val capturedAtEpochMillis: Long?,
)
