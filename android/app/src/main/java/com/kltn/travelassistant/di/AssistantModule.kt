package com.kltn.travelassistant.di

import com.kltn.travelassistant.feature.assistant.data.DefaultAssistantQueryRepository
import com.kltn.travelassistant.feature.assistant.data.NoOpAssistantIntentAnalytics
import com.kltn.travelassistant.feature.assistant.data.OkHttpAssistantApi
import com.kltn.travelassistant.feature.assistant.data.AssistantHttpApi
import com.kltn.travelassistant.feature.assistant.domain.AssistantIntentAnalytics
import com.kltn.travelassistant.feature.assistant.domain.AssistantQueryRepository
import dagger.Binds
import dagger.Module
import dagger.hilt.InstallIn
import dagger.hilt.components.SingletonComponent
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
internal abstract class AssistantModule {
    @Binds
    @Singleton
    abstract fun bindAssistantHttpApi(
        implementation: OkHttpAssistantApi,
    ): AssistantHttpApi

    @Binds
    @Singleton
    abstract fun bindAssistantQueryRepository(
        implementation: DefaultAssistantQueryRepository,
    ): AssistantQueryRepository

    @Binds
    @Singleton
    abstract fun bindAssistantIntentAnalytics(
        implementation: NoOpAssistantIntentAnalytics,
    ): AssistantIntentAnalytics
}
