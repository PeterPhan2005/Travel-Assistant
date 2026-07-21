package com.kltn.travelassistant.data.local.model

import com.kltn.travelassistant.data.local.entity.LocalItineraryEntity
import com.kltn.travelassistant.data.local.entity.LocalItineraryItemEntity

data class LocalItineraryWithItems(
    val itinerary: LocalItineraryEntity,
    val items: List<LocalItineraryItemEntity>,
)
