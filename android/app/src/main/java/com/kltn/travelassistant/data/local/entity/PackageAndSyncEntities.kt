package com.kltn.travelassistant.data.local.entity

import androidx.room.ColumnInfo
import androidx.room.Entity
import androidx.room.Index
import androidx.room.PrimaryKey

@Entity(
    tableName = "travel_packages",
    indices = [
        Index(
            value = ["city", "version"],
            name = "index_travel_packages_city_version",
            unique = true,
        ),
    ],
)
data class TravelPackageEntity(
    @PrimaryKey
    @ColumnInfo(name = "package_id")
    val packageId: String,
    @ColumnInfo(name = "city")
    val city: String,
    @ColumnInfo(name = "version")
    val version: String,
    @ColumnInfo(name = "manifest_json")
    val manifestJson: String,
    @ColumnInfo(name = "published_at_epoch_millis")
    val publishedAtEpochMillis: Long,
)

@Entity(
    tableName = "pending_sync_operations",
    indices = [
        Index(
            value = ["status", "created_at_epoch_millis", "operation_id"],
            name = "index_pending_sync_operations_status_created_id",
        ),
    ],
)
data class PendingSyncOperationEntity(
    @PrimaryKey
    @ColumnInfo(name = "operation_id")
    val operationId: String,
    @ColumnInfo(name = "operation_type")
    val operationType: String,
    @ColumnInfo(name = "entity_type")
    val entityType: String,
    @ColumnInfo(name = "entity_id")
    val entityId: String,
    @ColumnInfo(name = "payload_json")
    val payloadJson: String,
    @ColumnInfo(name = "status")
    val status: String,
    @ColumnInfo(name = "created_at_epoch_millis")
    val createdAtEpochMillis: Long,
    @ColumnInfo(name = "last_attempt_at_epoch_millis")
    val lastAttemptAtEpochMillis: Long?,
    @ColumnInfo(name = "attempt_count")
    val attemptCount: Int,
)
