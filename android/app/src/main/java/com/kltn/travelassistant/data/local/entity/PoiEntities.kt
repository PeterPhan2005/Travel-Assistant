package com.kltn.travelassistant.data.local.entity

import androidx.room.ColumnInfo
import androidx.room.Entity
import androidx.room.ForeignKey
import androidx.room.Index
import androidx.room.PrimaryKey

/**
 * Offline POI data.
 *
 * Externally generated identifiers remain strings, timestamps are Unix epoch milliseconds,
 * coordinates use SQLite REAL through [Double], and currency values use integer minor units.
 */
@Entity(
    tableName = "local_pois",
    indices = [
        Index(
            value = ["city", "category"],
            name = "index_local_pois_city_category",
        ),
    ],
)
data class LocalPoiEntity(
    @PrimaryKey
    @ColumnInfo(name = "poi_id")
    val poiId: String,
    @ColumnInfo(name = "name")
    val name: String,
    @ColumnInfo(name = "city")
    val city: String,
    @ColumnInfo(name = "area")
    val area: String?,
    @ColumnInfo(name = "category")
    val category: String,
    @ColumnInfo(name = "latitude")
    val latitude: Double,
    @ColumnInfo(name = "longitude")
    val longitude: Double,
    @ColumnInfo(name = "address")
    val address: String?,
    @ColumnInfo(name = "short_description")
    val shortDescription: String?,
    @ColumnInfo(name = "status")
    val status: String,
    @ColumnInfo(name = "updated_at_epoch_millis")
    val updatedAtEpochMillis: Long,
)

@Entity(
    tableName = "local_poi_aliases",
    foreignKeys = [
        ForeignKey(
            entity = LocalPoiEntity::class,
            parentColumns = ["poi_id"],
            childColumns = ["poi_id"],
            onDelete = ForeignKey.CASCADE,
        ),
    ],
    indices = [
        Index(value = ["poi_id"], name = "index_local_poi_aliases_poi_id"),
        Index(value = ["normalized_alias"], name = "index_local_poi_aliases_normalized_alias"),
    ],
)
data class LocalPoiAliasEntity(
    @PrimaryKey
    @ColumnInfo(name = "alias_id")
    val aliasId: String,
    @ColumnInfo(name = "poi_id")
    val poiId: String,
    @ColumnInfo(name = "alias")
    val alias: String,
    @ColumnInfo(name = "normalized_alias")
    val normalizedAlias: String,
    @ColumnInfo(name = "language_code")
    val languageCode: String?,
)

@Entity(
    tableName = "local_menu_items",
    foreignKeys = [
        ForeignKey(
            entity = LocalPoiEntity::class,
            parentColumns = ["poi_id"],
            childColumns = ["poi_id"],
            onDelete = ForeignKey.CASCADE,
        ),
    ],
    indices = [
        Index(value = ["poi_id"], name = "index_local_menu_items_poi_id"),
    ],
)
data class LocalMenuItemEntity(
    @PrimaryKey
    @ColumnInfo(name = "menu_item_id")
    val menuItemId: String,
    @ColumnInfo(name = "poi_id")
    val poiId: String,
    @ColumnInfo(name = "dish_name")
    val dishName: String,
    @ColumnInfo(name = "price_minor_units")
    val priceMinorUnits: Long,
    @ColumnInfo(name = "currency_code")
    val currencyCode: String,
    @ColumnInfo(name = "source_type")
    val sourceType: String,
    @ColumnInfo(name = "updated_at_epoch_millis")
    val updatedAtEpochMillis: Long,
)

@Entity(
    tableName = "local_narrations",
    foreignKeys = [
        ForeignKey(
            entity = LocalPoiEntity::class,
            parentColumns = ["poi_id"],
            childColumns = ["poi_id"],
            onDelete = ForeignKey.CASCADE,
        ),
    ],
    indices = [
        Index(
            value = ["poi_id", "language_code"],
            name = "index_local_narrations_poi_language",
            unique = true,
        ),
    ],
)
data class LocalNarrationEntity(
    @PrimaryKey
    @ColumnInfo(name = "narration_id")
    val narrationId: String,
    @ColumnInfo(name = "poi_id")
    val poiId: String,
    @ColumnInfo(name = "language_code")
    val languageCode: String,
    @ColumnInfo(name = "content")
    val content: String,
    @ColumnInfo(name = "verification_status")
    val verificationStatus: String,
    @ColumnInfo(name = "generated_at_epoch_millis")
    val generatedAtEpochMillis: Long,
    @ColumnInfo(name = "source_label")
    val sourceLabel: String? = null,
)

@Entity(
    tableName = "local_culture_items",
    indices = [
        Index(
            value = ["city", "area"],
            name = "index_local_culture_items_city_area",
        ),
    ],
)
data class LocalCultureEntity(
    @PrimaryKey
    @ColumnInfo(name = "culture_item_id")
    val cultureItemId: String,
    @ColumnInfo(name = "city")
    val city: String,
    @ColumnInfo(name = "area")
    val area: String?,
    @ColumnInfo(name = "topic")
    val topic: String,
    @ColumnInfo(name = "content")
    val content: String,
    @ColumnInfo(name = "verification_status")
    val verificationStatus: String,
)
