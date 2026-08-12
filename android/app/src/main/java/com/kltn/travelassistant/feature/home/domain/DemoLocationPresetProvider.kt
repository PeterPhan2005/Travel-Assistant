package com.kltn.travelassistant.feature.home.domain

import com.kltn.travelassistant.data.location.DeviceLocation

data class DemoLocationPreset(
    val id: String,
    val label: String,
    val location: DeviceLocation,
) {
    init {
        require(id.isNotBlank() && id.length <= MAX_ID_LENGTH && id.none(Char::isISOControl))
        require(
            label.isNotBlank() &&
                label.length <= MAX_LABEL_LENGTH &&
                label.none(Char::isISOControl),
        )
        require(location.latitude.isFinite() && location.latitude in -90.0..90.0)
        require(location.longitude.isFinite() && location.longitude in -180.0..180.0)
    }

    private companion object {
        const val MAX_ID_LENGTH = 40
        const val MAX_LABEL_LENGTH = 80
    }
}

interface DemoLocationPresetProvider {
    val presets: List<DemoLocationPreset>

    fun findById(id: String): DemoLocationPreset? = presets.firstOrNull { preset ->
        preset.id == id
    }
}
