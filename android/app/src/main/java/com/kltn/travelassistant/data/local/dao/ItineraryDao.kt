package com.kltn.travelassistant.data.local.dao

import androidx.room.Dao
import androidx.room.Query
import androidx.room.Transaction
import androidx.room.Upsert
import com.kltn.travelassistant.data.local.entity.LocalItineraryEntity
import com.kltn.travelassistant.data.local.entity.LocalItineraryItemEntity
import com.kltn.travelassistant.data.local.model.LocalItineraryWithItems

@Dao
abstract class ItineraryDao {
    @Upsert
    abstract suspend fun upsertItinerary(itinerary: LocalItineraryEntity)

    @Upsert
    abstract suspend fun upsertItineraryItems(items: List<LocalItineraryItemEntity>)

    @Query("SELECT * FROM local_itineraries WHERE itinerary_id = :itineraryId LIMIT 1")
    abstract suspend fun getItineraryById(itineraryId: String): LocalItineraryEntity?

    @Query(
        """
        SELECT * FROM local_itinerary_items
        WHERE itinerary_id = :itineraryId
        ORDER BY position, itinerary_item_id
        """,
    )
    abstract suspend fun getItemsForItinerary(
        itineraryId: String,
    ): List<LocalItineraryItemEntity>

    @Transaction
    open suspend fun getItineraryWithItems(itineraryId: String): LocalItineraryWithItems? {
        val itinerary = getItineraryById(itineraryId) ?: return null
        return LocalItineraryWithItems(
            itinerary = itinerary,
            items = getItemsForItinerary(itineraryId),
        )
    }

    /** Child items are removed by the itinerary foreign key's CASCADE behavior. */
    @Query("DELETE FROM local_itineraries WHERE itinerary_id = :itineraryId")
    abstract suspend fun deleteItinerary(itineraryId: String): Int
}
