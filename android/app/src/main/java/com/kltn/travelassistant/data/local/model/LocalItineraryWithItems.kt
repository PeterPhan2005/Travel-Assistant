package com.kltn.travelassistant.data.local.model

import androidx.room.Embedded
import androidx.room.Relation
import com.kltn.travelassistant.data.local.entity.LocalItineraryEntity
import com.kltn.travelassistant.data.local.entity.LocalItineraryItemEntity

data class LocalItineraryWithItems(
    @Embedded
    val itinerary: LocalItineraryEntity,
    @Relation(
        parentColumn = "itinerary_id",
        entityColumn = "itinerary_id",
    )
    val items: List<LocalItineraryItemEntity>,
)
