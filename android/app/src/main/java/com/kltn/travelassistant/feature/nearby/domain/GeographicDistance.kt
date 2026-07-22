package com.kltn.travelassistant.feature.nearby.domain

import kotlin.math.atan2
import kotlin.math.cos
import kotlin.math.sin
import kotlin.math.sqrt

data class GeographicCoordinate(
    val latitude: Double,
    val longitude: Double,
) {
    val isValid: Boolean
        get() = latitude.isFinite() &&
            longitude.isFinite() &&
            latitude in -90.0..90.0 &&
            longitude in -180.0..180.0
}

object GeographicDistance {
    private const val EARTH_RADIUS_METRES = 6_371_000.0

    fun metresBetween(
        origin: GeographicCoordinate,
        destination: GeographicCoordinate,
    ): Double? {
        if (!origin.isValid || !destination.isValid) return null

        val originLatitude = Math.toRadians(origin.latitude)
        val destinationLatitude = Math.toRadians(destination.latitude)
        val latitudeDelta = destinationLatitude - originLatitude
        val longitudeDelta = Math.toRadians(destination.longitude - origin.longitude)
        val haversine = (sin(latitudeDelta / 2).let { it * it } +
            cos(originLatitude) * cos(destinationLatitude) *
            sin(longitudeDelta / 2).let { it * it }).coerceIn(0.0, 1.0)
        val angularDistance = 2 * atan2(sqrt(haversine), sqrt(1 - haversine))
        return EARTH_RADIUS_METRES * angularDistance
    }
}
