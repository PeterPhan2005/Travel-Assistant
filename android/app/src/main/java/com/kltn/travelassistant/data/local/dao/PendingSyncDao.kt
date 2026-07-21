package com.kltn.travelassistant.data.local.dao

import androidx.room.Dao
import androidx.room.Query
import androidx.room.Upsert
import com.kltn.travelassistant.data.local.entity.PendingSyncOperationEntity

@Dao
interface PendingSyncDao {
    @Upsert
    suspend fun enqueue(operation: PendingSyncOperationEntity)

    @Query(
        """
        SELECT * FROM pending_sync_operations
        WHERE status = :status
        ORDER BY created_at_epoch_millis, operation_id
        """,
    )
    suspend fun getOperationsByStatus(status: String): List<PendingSyncOperationEntity>

    @Query("SELECT * FROM pending_sync_operations WHERE operation_id = :operationId LIMIT 1")
    suspend fun getOperationById(operationId: String): PendingSyncOperationEntity?

    @Query(
        """
        UPDATE pending_sync_operations
        SET status = :status, last_attempt_at_epoch_millis = :attemptedAtEpochMillis,
            attempt_count = attempt_count + 1
        WHERE operation_id = :operationId
        """,
    )
    suspend fun updateStatus(
        operationId: String,
        status: String,
        attemptedAtEpochMillis: Long,
    ): Int

    @Query("DELETE FROM pending_sync_operations WHERE operation_id = :operationId")
    suspend fun remove(operationId: String): Int
}
