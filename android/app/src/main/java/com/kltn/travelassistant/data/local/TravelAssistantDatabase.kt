package com.kltn.travelassistant.data.local

import androidx.room.Database
import androidx.room.RoomDatabase
import com.kltn.travelassistant.data.local.dao.ItineraryDao
import com.kltn.travelassistant.data.local.dao.PendingSyncDao
import com.kltn.travelassistant.data.local.dao.PoiContentDao
import com.kltn.travelassistant.data.local.dao.TravelPackageDao
import com.kltn.travelassistant.data.local.entity.LocalCultureEntity
import com.kltn.travelassistant.data.local.entity.LocalItineraryEntity
import com.kltn.travelassistant.data.local.entity.LocalItineraryItemEntity
import com.kltn.travelassistant.data.local.entity.LocalMenuItemEntity
import com.kltn.travelassistant.data.local.entity.LocalNarrationEntity
import com.kltn.travelassistant.data.local.entity.LocalPoiAliasEntity
import com.kltn.travelassistant.data.local.entity.LocalPoiEntity
import com.kltn.travelassistant.data.local.entity.PendingSyncOperationEntity
import com.kltn.travelassistant.data.local.entity.TravelPackageEntity

/**
 * Initial local database schema.
 *
 * Every future schema change must increment [version], preserve exported schemas, add explicit
 * migrations, and include migration tests. Destructive migration fallback is intentionally absent.
 */
@Database(
    entities = [
        LocalPoiEntity::class,
        LocalPoiAliasEntity::class,
        LocalMenuItemEntity::class,
        LocalNarrationEntity::class,
        LocalCultureEntity::class,
        LocalItineraryEntity::class,
        LocalItineraryItemEntity::class,
        TravelPackageEntity::class,
        PendingSyncOperationEntity::class,
    ],
    version = 1,
    exportSchema = true,
)
abstract class TravelAssistantDatabase : RoomDatabase() {
    abstract fun poiContentDao(): PoiContentDao

    abstract fun itineraryDao(): ItineraryDao

    abstract fun travelPackageDao(): TravelPackageDao

    abstract fun pendingSyncDao(): PendingSyncDao

    companion object {
        const val DATABASE_NAME = "travel_assistant.db"
    }
}
