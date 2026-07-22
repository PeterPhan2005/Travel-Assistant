package com.kltn.travelassistant.data.local.model

import com.kltn.travelassistant.data.local.entity.LocalMenuItemEntity
import com.kltn.travelassistant.data.local.entity.LocalNarrationEntity
import com.kltn.travelassistant.data.local.entity.LocalPoiEntity

data class LocalPoiDetailSnapshot(
    val poi: LocalPoiEntity,
    val menuItems: List<LocalMenuItemEntity>,
    val narration: LocalNarrationEntity?,
)
