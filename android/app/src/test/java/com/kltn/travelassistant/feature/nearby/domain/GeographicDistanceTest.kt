package com.kltn.travelassistant.feature.nearby.domain

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class GeographicDistanceTest {
    @Test
    fun sameCoordinatesReturnZero() {
        val coordinate = GeographicCoordinate(10.7725, 106.6980)

        assertEquals(0.0, GeographicDistance.metresBetween(coordinate, coordinate)!!, 0.0)
    }

    @Test
    fun knownHcmcCoordinatePairReturnsDeterministicReasonableDistance() {
        val distance = GeographicDistance.metresBetween(
            GeographicCoordinate(10.7725, 106.6980),
            GeographicCoordinate(10.7799, 106.7000),
        )!!

        assertEquals(851.0, distance, 2.0)
    }

    @Test
    fun invalidCoordinatesFailSafely() {
        assertNull(
            GeographicDistance.metresBetween(
                GeographicCoordinate(91.0, 106.0),
                GeographicCoordinate(10.0, 106.0),
            ),
        )
        assertNull(
            GeographicDistance.metresBetween(
                GeographicCoordinate(Double.NaN, 106.0),
                GeographicCoordinate(10.0, 106.0),
            ),
        )
    }

    @Test
    fun rankingPlacesNearestFirstAndUsesStableNameThenIdTies() {
        val ranked = NearbyPoiRanking.sort(
            listOf(
                poi(id = "z", name = "Xa", distance = 20.0),
                poi(id = "b", name = "Bến Thành", distance = 10.0),
                poi(id = "a", name = "Bến Thành", distance = 10.0),
                poi(id = "c", name = "Ánh Sao", distance = 10.0),
            ),
        )

        assertEquals(listOf("c", "a", "b", "z"), ranked.map(NearbyPoi::poiId))
        assertTrue(ranked.zipWithNext().all { (first, second) ->
            first.distanceMeters <= second.distanceMeters
        })
    }

    private fun poi(id: String, name: String, distance: Double) = NearbyPoi(
        poiId = id,
        displayName = name,
        category = "landmark",
        categoryLabel = PoiCategoryLabel.LANDMARK,
        distanceMeters = distance,
    )
}
