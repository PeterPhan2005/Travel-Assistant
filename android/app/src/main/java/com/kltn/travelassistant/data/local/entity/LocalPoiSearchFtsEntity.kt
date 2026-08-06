package com.kltn.travelassistant.data.local.entity

import androidx.room.ColumnInfo
import androidx.room.Entity
import androidx.room.Fts4
import androidx.room.FtsOptions
import com.kltn.travelassistant.data.local.dao.PoiContentDao

/**
 * Derived full-text index for the canonical package-owned POI graph.
 *
 * This table is not a second POI model. Every row is rebuilt from [LocalPoiEntity],
 * [LocalPoiAliasEntity], and [LocalMenuItemEntity] through [PoiContentDao].
 */
@Entity(tableName = "local_poi_search_fts")
@Fts4(
    tokenizer = FtsOptions.TOKENIZER_UNICODE61,
    notIndexed = ["poi_id"],
)
data class LocalPoiSearchFtsEntity(
    @ColumnInfo(name = "poi_id")
    val poiId: String,
    @ColumnInfo(name = "normalized_name")
    val normalizedName: String,
    @ColumnInfo(name = "normalized_aliases")
    val normalizedAliases: String,
    @ColumnInfo(name = "normalized_dishes")
    val normalizedDishes: String,
    @ColumnInfo(name = "normalized_categories")
    val normalizedCategories: String,
)
