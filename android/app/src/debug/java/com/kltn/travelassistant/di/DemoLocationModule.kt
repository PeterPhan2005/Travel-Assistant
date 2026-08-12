package com.kltn.travelassistant.di

import com.kltn.travelassistant.feature.home.domain.DebugDemoLocationPresetProvider
import com.kltn.travelassistant.feature.home.domain.DemoLocationPresetProvider
import dagger.Binds
import dagger.Module
import dagger.hilt.InstallIn
import dagger.hilt.components.SingletonComponent
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
abstract class DemoLocationModule {
    @Binds
    @Singleton
    abstract fun bindDemoLocationPresetProvider(
        provider: DebugDemoLocationPresetProvider,
    ): DemoLocationPresetProvider
}
