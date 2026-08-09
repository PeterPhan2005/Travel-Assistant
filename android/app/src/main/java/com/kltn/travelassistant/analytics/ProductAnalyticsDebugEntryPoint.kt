package com.kltn.travelassistant.analytics

import dagger.hilt.EntryPoint
import dagger.hilt.InstallIn
import dagger.hilt.components.SingletonComponent

@EntryPoint
@InstallIn(SingletonComponent::class)
internal interface ProductAnalyticsDebugEntryPoint {
    fun productAnalytics(): ProductAnalytics

    fun debugProductAnalyticsInspector(): DebugProductAnalyticsInspector
}
