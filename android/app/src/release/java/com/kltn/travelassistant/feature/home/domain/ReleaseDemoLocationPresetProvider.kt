package com.kltn.travelassistant.feature.home.domain

import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class ReleaseDemoLocationPresetProvider @Inject constructor() : DemoLocationPresetProvider {
    override val presets: List<DemoLocationPreset> = emptyList()
}
