package com.kltn.travelassistant.navigation.external

import com.kltn.travelassistant.feature.poi.domain.PoiNavigationTarget
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class ExternalNavigationTargetValidationTest {
    @Test
    fun validTargetAcceptsInclusiveCoordinateBounds() {
        assertTrue(target(latitude = -90.0, longitude = -180.0).isValidForExternalNavigation())
        assertTrue(target(latitude = 90.0, longitude = 180.0).isValidForExternalNavigation())
    }

    @Test
    fun invalidTargetRejectsNonFiniteAndOutOfRangeCoordinates() {
        listOf(
            target(latitude = Double.NaN),
            target(latitude = Double.POSITIVE_INFINITY),
            target(longitude = Double.NEGATIVE_INFINITY),
            target(latitude = -90.000001),
            target(latitude = 90.000001),
            target(longitude = -180.000001),
            target(longitude = 180.000001),
        ).forEach { invalidTarget ->
            assertFalse(invalidTarget.isValidForExternalNavigation())
        }
    }

    @Test
    fun invalidTargetRejectsBlankIdentityAndDisplayName() {
        assertFalse(target(poiId = " ").isValidForExternalNavigation())
        assertFalse(target(displayName = "\n").isValidForExternalNavigation())
    }

    private fun target(
        poiId: String = "poi-1",
        displayName: String = "Chợ Bến Thành",
        latitude: Double = 10.7725,
        longitude: Double = 106.6980,
    ) = PoiNavigationTarget(
        poiId = poiId,
        displayName = displayName,
        latitude = latitude,
        longitude = longitude,
    )
}
