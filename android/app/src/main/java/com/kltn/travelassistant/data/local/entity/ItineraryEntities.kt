package com.kltn.travelassistant.data.local.entity

import androidx.room.ColumnInfo
import androidx.room.Entity
import androidx.room.ForeignKey
import androidx.room.Index
import androidx.room.PrimaryKey

@Entity(tableName = "local_itineraries")
data class LocalItineraryEntity(
    @PrimaryKey
    @ColumnInfo(name = "itinerary_id")
    val itineraryId: String,
    @ColumnInfo(name = "title")
    val title: String,
    @ColumnInfo(name = "created_at_epoch_millis")
    val createdAtEpochMillis: Long,
    @ColumnInfo(name = "updated_at_epoch_millis")
    val updatedAtEpochMillis: Long,
)

@Entity(
    tableName = "local_itinerary_items",
    foreignKeys = [
        ForeignKey(
            entity = LocalItineraryEntity::class,
            parentColumns = ["itinerary_id"],
            childColumns = ["itinerary_id"],
            onDelete = ForeignKey.CASCADE,
        ),
        // Preserve a user's itinerary item if downloaded POI content is removed.
        ForeignKey(
            entity = LocalPoiEntity::class,
            parentColumns = ["poi_id"],
            childColumns = ["poi_id"],
            onDelete = ForeignKey.SET_NULL,
        ),
    ],
    indices = [
        Index(
            value = ["itinerary_id", "position"],
            name = "index_local_itinerary_items_itinerary_position",
            unique = true,
        ),
        Index(value = ["poi_id"], name = "index_local_itinerary_items_poi_id"),
    ],
)
data class LocalItineraryItemEntity(
    @PrimaryKey
    @ColumnInfo(name = "itinerary_item_id")
    val itineraryItemId: String,
    @ColumnInfo(name = "itinerary_id")
    val itineraryId: String,
    @ColumnInfo(name = "poi_id")
    val poiId: String?,
    @ColumnInfo(name = "title")
    val title: String,
    @ColumnInfo(name = "position")
    val position: Int,
    @ColumnInfo(name = "start_at_epoch_millis")
    val startAtEpochMillis: Long?,
    @ColumnInfo(name = "end_at_epoch_millis")
    val endAtEpochMillis: Long?,
    @ColumnInfo(name = "travel_time_minutes")
    val travelTimeMinutes: Int?,
    @ColumnInfo(name = "notes")
    val notes: String?,
)
