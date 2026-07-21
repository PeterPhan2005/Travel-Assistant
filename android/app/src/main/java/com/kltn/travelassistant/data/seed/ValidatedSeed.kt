package com.kltn.travelassistant.data.seed

import com.kltn.travelassistant.data.local.entity.LocalCultureEntity
import com.kltn.travelassistant.data.local.entity.LocalMenuItemEntity
import com.kltn.travelassistant.data.local.entity.LocalNarrationEntity
import com.kltn.travelassistant.data.local.entity.LocalPoiAliasEntity
import com.kltn.travelassistant.data.local.entity.LocalPoiEntity
import com.kltn.travelassistant.data.local.entity.TravelPackageEntity

data class ValidatedSeed(
    val travelPackage: TravelPackageEntity,
    val pois: List<LocalPoiEntity>,
    val aliases: List<LocalPoiAliasEntity>,
    val menuItems: List<LocalMenuItemEntity>,
    val narrations: List<LocalNarrationEntity>,
    val cultureItems: List<LocalCultureEntity>,
) {
    val counts = SeedRecordCounts(
        pois = pois.size,
        aliases = aliases.size,
        menuItems = menuItems.size,
        narrations = narrations.size,
        cultureItems = cultureItems.size,
    )
}

data class SeedRecordCounts(
    val pois: Int,
    val aliases: Int,
    val menuItems: Int,
    val narrations: Int,
    val cultureItems: Int,
)
