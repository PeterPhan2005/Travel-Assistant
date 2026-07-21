package com.kltn.travelassistant.di

import com.kltn.travelassistant.data.repository.AppInfoRepository
import com.kltn.travelassistant.data.repository.DefaultAppInfoRepository
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
}
