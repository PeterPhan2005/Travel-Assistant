package com.kltn.travelassistant.data.local.dao

import androidx.room.Dao
import androidx.room.Query
import androidx.room.Transaction
import androidx.room.Upsert
import com.kltn.travelassistant.data.local.entity.LocalItineraryEntity
import com.kltn.travelassistant.data.local.entity.LocalItineraryItemEntity
import com.kltn.travelassistant.data.local.model.LocalItineraryWithItems
import kotlinx.coroutines.flow.Flow

@Dao
abstract class ItineraryDao {
    @Upsert
    abstract suspend fun upsertItinerary(itinerary: LocalItineraryEntity)

    @Upsert
    abstract suspend fun upsertItineraryItems(items: List<LocalItineraryItemEntity>)

    @Query(
        """
        SELECT * FROM local_itineraries
        WHERE account_key = :accountKey AND itinerary_id = :itineraryId
        LIMIT 1
        """,
    )
    abstract suspend fun getItineraryById(
        accountKey: String,
        itineraryId: String,
    ): LocalItineraryEntity?

    @Transaction
    @Query(
        """
        SELECT * FROM local_itineraries
        WHERE account_key = :accountKey AND is_deleted = 0
        ORDER BY local_date DESC, updated_at_epoch_millis DESC, itinerary_id
        """,
    )
    abstract fun observeReadableItineraries(
        accountKey: String,
    ): Flow<List<LocalItineraryWithItems>>

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
    open suspend fun getItineraryWithItems(
        accountKey: String,
        itineraryId: String,
    ): LocalItineraryWithItems? {
        val itinerary = getItineraryById(accountKey, itineraryId) ?: return null
        return LocalItineraryWithItems(
            itinerary = itinerary,
            items = getItemsForItinerary(itineraryId),
        )
    }

    @Transaction
    open suspend fun replaceSnapshot(
        itinerary: LocalItineraryEntity,
        items: List<LocalItineraryItemEntity>,
    ) {
        upsertItinerary(itinerary)
        deleteItemsForItinerary(itinerary.itineraryId)
        upsertItineraryItems(items)
    }

    @Query("DELETE FROM local_itinerary_items WHERE itinerary_id = :itineraryId")
    abstract suspend fun deleteItemsForItinerary(itineraryId: String): Int

    @Query(
        """
        UPDATE local_itineraries
        SET is_deleted = 1,
            local_revision = local_revision + 1,
            sync_state = 'pending',
            updated_at_epoch_millis = :updatedAtEpochMillis
        WHERE account_key = :accountKey AND itinerary_id = :itineraryId
          AND is_deleted = 0 AND local_revision < 9223372036854775807
        """,
    )
    protected abstract suspend fun markDeleted(
        accountKey: String,
        itineraryId: String,
        updatedAtEpochMillis: Long,
    ): Int

    @Transaction
    open suspend fun markDeletedAndRemoveItems(
        accountKey: String,
        itineraryId: String,
        updatedAtEpochMillis: Long,
    ): Boolean {
        val changed = markDeleted(accountKey, itineraryId, updatedAtEpochMillis) == 1
        if (changed) deleteItemsForItinerary(itineraryId)
        return changed
    }

    @Query(
        """
        UPDATE local_itineraries
        SET server_revision = :serverRevision, sync_state = 'synced'
        WHERE account_key = :accountKey AND itinerary_id = :itineraryId
          AND local_revision = :expectedLocalRevision
        """,
    )
    abstract suspend fun completeSync(
        accountKey: String,
        itineraryId: String,
        expectedLocalRevision: Long,
        serverRevision: Long,
    ): Int

    @Query(
        """
        UPDATE local_itineraries
        SET server_revision = :serverRevision
        WHERE account_key = :accountKey AND itinerary_id = :itineraryId
          AND local_revision > :staleLocalRevision
          AND server_revision < :serverRevision
          AND sync_state = 'pending'
        """,
    )
    abstract suspend fun recordServerRevisionForNewerLocalState(
        accountKey: String,
        itineraryId: String,
        staleLocalRevision: Long,
        serverRevision: Long,
    ): Int

    @Query(
        """
        UPDATE local_itineraries
        SET sync_state = :syncState
        WHERE account_key = :accountKey AND itinerary_id = :itineraryId
          AND local_revision = :expectedLocalRevision
        """,
    )
    abstract suspend fun markSyncState(
        accountKey: String,
        itineraryId: String,
        expectedLocalRevision: Long,
        syncState: String,
    ): Int

    @Query(
        """
        UPDATE local_itineraries
        SET sync_state = :syncState
        WHERE itinerary_id = :itineraryId AND sync_state = 'pending'
        """,
    )
    abstract suspend fun markPendingSyncStateByItineraryId(
        itineraryId: String,
        syncState: String,
    ): Int

    /** Child items are removed by the itinerary foreign key's CASCADE behavior. */
    @Query("DELETE FROM local_itineraries WHERE itinerary_id = :itineraryId")
    abstract suspend fun deleteItinerary(itineraryId: String): Int
}
