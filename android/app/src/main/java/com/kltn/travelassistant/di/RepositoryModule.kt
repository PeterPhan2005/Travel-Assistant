package com.kltn.travelassistant.di

import com.kltn.travelassistant.data.repository.AppInfoRepository
import com.kltn.travelassistant.data.repository.DefaultAppInfoRepository
import com.kltn.travelassistant.data.repository.RoomNearbySearchRepository
import com.kltn.travelassistant.data.repository.RoomPoiDetailRepository
import com.kltn.travelassistant.feature.nearby.domain.NearbySearchRepository
import com.kltn.travelassistant.feature.poi.domain.PoiDetailRepository
import dagger.Binds
import dagger.Module
import dagger.hilt.InstallIn
import dagger.hilt.components.SingletonComponent
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
abstract class RepositoryModule {
    @Binds
    @Singleton
    abstract fun bindAppInfoRepository(
        implementation: DefaultAppInfoRepository,
    ): AppInfoRepository

    @Binds
    @Singleton
    abstract fun bindNearbySearchRepository(
        implementation: RoomNearbySearchRepository,
    ): NearbySearchRepository

    @Binds
    @Singleton
    abstract fun bindPoiDetailRepository(
        implementation: RoomPoiDetailRepository,
    ): PoiDetailRepository
}
