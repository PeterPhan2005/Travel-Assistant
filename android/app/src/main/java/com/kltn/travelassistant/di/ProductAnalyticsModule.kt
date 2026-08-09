package com.kltn.travelassistant.di

import com.kltn.travelassistant.BuildConfig
import com.kltn.travelassistant.analytics.DebugProductAnalyticsInspector
import com.kltn.travelassistant.analytics.InMemoryProductAnalytics
import com.kltn.travelassistant.analytics.ProductAnalytics
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.components.SingletonComponent
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
internal object ProductAnalyticsModule {
    @Provides
    @Singleton
    fun provideProductAnalyticsRuntime(): InMemoryProductAnalytics =
        InMemoryProductAnalytics(enabled = BuildConfig.DEBUG)

    @Provides
    @Singleton
    fun provideProductAnalytics(
        runtime: InMemoryProductAnalytics,
    ): ProductAnalytics = runtime

    @Provides
    @Singleton
    fun provideDebugProductAnalyticsInspector(
        runtime: InMemoryProductAnalytics,
    ): DebugProductAnalyticsInspector = runtime
}
