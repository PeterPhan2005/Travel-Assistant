package com.kltn.travelassistant.di

import com.kltn.travelassistant.feature.home.domain.DemoLocationPresetProvider
import com.kltn.travelassistant.feature.home.domain.ReleaseDemoLocationPresetProvider
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
        provider: ReleaseDemoLocationPresetProvider,
    ): DemoLocationPresetProvider
}
