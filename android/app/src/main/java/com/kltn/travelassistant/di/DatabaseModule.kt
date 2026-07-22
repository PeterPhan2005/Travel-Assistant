package com.kltn.travelassistant.di

import android.content.Context
import androidx.room.Room
import com.kltn.travelassistant.data.local.TravelAssistantDatabase
import com.kltn.travelassistant.data.local.DatabaseMigrations
import com.kltn.travelassistant.data.local.dao.ItineraryDao
import com.kltn.travelassistant.data.local.dao.PendingSyncDao
import com.kltn.travelassistant.data.local.dao.PoiContentDao
import com.kltn.travelassistant.data.local.dao.TravelPackageDao
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.android.qualifiers.ApplicationContext
import dagger.hilt.components.SingletonComponent
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
object DatabaseModule {
    @Provides
    @Singleton
    fun provideDatabase(
        @ApplicationContext context: Context,
    ): TravelAssistantDatabase = Room.databaseBuilder(
        context,
        TravelAssistantDatabase::class.java,
        TravelAssistantDatabase.DATABASE_NAME,
    ).addMigrations(DatabaseMigrations.MIGRATION_1_2)
        .build()

    @Provides
    fun providePoiContentDao(database: TravelAssistantDatabase): PoiContentDao =
        database.poiContentDao()

    @Provides
    fun provideItineraryDao(database: TravelAssistantDatabase): ItineraryDao =
        database.itineraryDao()

    @Provides
    fun provideTravelPackageDao(database: TravelAssistantDatabase): TravelPackageDao =
        database.travelPackageDao()

    @Provides
    fun providePendingSyncDao(database: TravelAssistantDatabase): PendingSyncDao =
        database.pendingSyncDao()
}
