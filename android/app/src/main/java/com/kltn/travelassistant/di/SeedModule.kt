package com.kltn.travelassistant.di

import com.kltn.travelassistant.data.seed.BundledHcmcSeedSource
import com.kltn.travelassistant.data.seed.CuratedSeedImporter
import com.kltn.travelassistant.data.seed.RoomCuratedSeedImporter
import com.kltn.travelassistant.data.seed.SeedSource
import dagger.Binds
import dagger.Module
import dagger.hilt.InstallIn
import dagger.hilt.components.SingletonComponent
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
abstract class SeedModule {
    @Binds
    @Singleton
    abstract fun bindSeedSource(source: BundledHcmcSeedSource): SeedSource

    @Binds
    @Singleton
    abstract fun bindCuratedSeedImporter(importer: RoomCuratedSeedImporter): CuratedSeedImporter
}
