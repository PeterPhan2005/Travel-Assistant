package com.kltn.travelassistant.data.local.dao

import androidx.room.Dao
import androidx.room.Query
import androidx.room.Upsert
import com.kltn.travelassistant.data.local.entity.TravelPackageEntity
import kotlinx.coroutines.flow.Flow

@Dao
interface TravelPackageDao {
    @Upsert
    suspend fun upsertPackage(travelPackage: TravelPackageEntity)

    @Query("SELECT * FROM travel_packages WHERE city = :city AND version = :version LIMIT 1")
    suspend fun getPackage(city: String, version: String): TravelPackageEntity?

    @Query(
        """
        SELECT * FROM travel_packages
        WHERE package_id = :packageId AND version = :version
        LIMIT 1
        """,
    )
    suspend fun getPackageByIdAndVersion(packageId: String, version: String): TravelPackageEntity?

    @Query(
        """
        SELECT * FROM travel_packages
        WHERE city = :city
        ORDER BY published_at_epoch_millis DESC, version DESC, package_id DESC
        LIMIT 1
        """,
    )
    fun observeLatestPackage(city: String): Flow<TravelPackageEntity?>
}
