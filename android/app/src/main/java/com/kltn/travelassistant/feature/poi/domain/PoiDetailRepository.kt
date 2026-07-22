package com.kltn.travelassistant.feature.poi.domain

import com.kltn.travelassistant.feature.nearby.domain.PoiCategoryLabel

data class PoiDetail(
    val poiId: String,
    val name: String,
    val category: PoiCategoryLabel,
    val city: String,
    val area: String?,
    val address: String?,
    val shortDescription: String?,
    val menuItems: List<PoiMenuItem>,
    val narration: PoiNarration?,
)

data class PoiMenuItem(
    val dishName: String,
    val priceMinorUnits: Long,
    val currencyCode: String,
    val sourceType: String,
    val updatedAtEpochMillis: Long,
)

data class PoiNarration(
    val content: String,
    val sourceLabel: String,
)

sealed interface PoiDetailResult {
    data class Success(val detail: PoiDetail) : PoiDetailResult

    data object NotFound : PoiDetailResult

    data object DatabaseError : PoiDetailResult
}

interface PoiDetailRepository {
    suspend fun getPoiDetail(
        poiId: String,
        languageCode: String,
    ): PoiDetailResult
}
