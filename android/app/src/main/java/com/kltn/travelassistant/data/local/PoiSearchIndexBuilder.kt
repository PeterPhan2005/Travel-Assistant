package com.kltn.travelassistant.data.local

import com.kltn.travelassistant.data.local.entity.LocalMenuItemEntity
import com.kltn.travelassistant.data.local.entity.LocalPoiAliasEntity
import com.kltn.travelassistant.data.local.entity.LocalPoiEntity
import com.kltn.travelassistant.data.local.entity.LocalPoiSearchFtsEntity
import com.kltn.travelassistant.feature.nearby.domain.PoiCategoryLabels
import com.kltn.travelassistant.feature.nearby.domain.VietnameseTextNormalizer

internal object PoiSearchIndexBuilder {
    fun build(
        poi: LocalPoiEntity,
        aliases: List<LocalPoiAliasEntity>,
        menuItems: List<LocalMenuItemEntity>,
    ): LocalPoiSearchFtsEntity = LocalPoiSearchFtsEntity(
        poiId = poi.poiId,
        normalizedName = VietnameseTextNormalizer.normalize(poi.name),
        normalizedAliases = normalizedJoinedText(
            aliases.sortedWith(compareBy(LocalPoiAliasEntity::aliasId)).flatMap { alias ->
                listOf(alias.alias, alias.normalizedAlias)
            },
        ),
        normalizedDishes = normalizedJoinedText(
            menuItems.sortedWith(compareBy(LocalMenuItemEntity::menuItemId))
                .map(LocalMenuItemEntity::dishName),
        ),
        normalizedCategories = normalizedJoinedText(
            listOf(
                poi.category,
                PoiCategoryLabels.searchTextFor(PoiCategoryLabels.labelFor(poi.category)),
            ),
        ),
    )

    private fun normalizedJoinedText(values: List<String>): String = values
        .asSequence()
        .map(VietnameseTextNormalizer::normalize)
        .filter(String::isNotEmpty)
        .distinct()
        .joinToString(separator = " ")
}
