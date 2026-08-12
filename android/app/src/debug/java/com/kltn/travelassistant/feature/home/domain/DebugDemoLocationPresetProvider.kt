package com.kltn.travelassistant.feature.home.domain

import com.kltn.travelassistant.data.location.DeviceLocation
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class DebugDemoLocationPresetProvider @Inject constructor() : DemoLocationPresetProvider {
    override val presets: List<DemoLocationPreset> = listOf(
        DemoLocationPreset(
            id = "hcmc",
            label = "Demo: TP.HCM",
            // data/curated/hcmc/package-v1.yaml, hcmc-poi-central-post-office.
            location = DeviceLocation(
                latitude = 10.7799,
                longitude = 106.7,
                accuracyMeters = null,
                capturedAtEpochMillis = null,
            ),
        ),
        DemoLocationPreset(
            id = "bangkok",
            label = "Demo: Bangkok",
            // data/curated/bangkok/package-v1.yaml, bkk-poi-wat-pho.
            location = DeviceLocation(
                latitude = 13.746508,
                longitude = 100.493096,
                accuracyMeters = null,
                capturedAtEpochMillis = null,
            ),
        ),
    )
}
