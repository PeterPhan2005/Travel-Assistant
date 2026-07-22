package com.kltn.travelassistant.di

import com.kltn.travelassistant.data.location.AndroidLocationClient
import com.kltn.travelassistant.data.location.LocationClient
import dagger.Binds
import dagger.Module
import dagger.hilt.InstallIn
import dagger.hilt.components.SingletonComponent
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
abstract class LocationModule {
    @Binds
    @Singleton
    abstract fun bindLocationClient(implementation: AndroidLocationClient): LocationClient
}
