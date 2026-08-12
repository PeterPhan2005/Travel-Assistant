package com.kltn.travelassistant.feature.home.domain

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class DebugDemoLocationPresetProviderTest {
    @Test
    fun exposesExactlyRepositoryGroundedHcmcAndBangkokPresets() {
        val presets = DebugDemoLocationPresetProvider().presets

        assertEquals(listOf("hcmc", "bangkok"), presets.map(DemoLocationPreset::id))
        assertEquals(listOf("Demo: TP.HCM", "Demo: Bangkok"), presets.map(DemoLocationPreset::label))
        assertEquals(10.7799, presets[0].location.latitude, 0.0)
        assertEquals(106.7, presets[0].location.longitude, 0.0)
        assertEquals(13.746508, presets[1].location.latitude, 0.0)
        assertEquals(100.493096, presets[1].location.longitude, 0.0)
        presets.forEach { preset ->
            assertNull(preset.location.accuracyMeters)
            assertNull(preset.location.capturedAtEpochMillis)
        }
    }
}
