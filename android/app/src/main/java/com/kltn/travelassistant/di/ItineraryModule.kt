package com.kltn.travelassistant.di

import com.kltn.travelassistant.feature.itinerary.data.DefaultItineraryDraftGenerator
import com.kltn.travelassistant.feature.itinerary.data.ItineraryHttpApi
import com.kltn.travelassistant.feature.itinerary.data.ItineraryWorkScheduler
import com.kltn.travelassistant.feature.itinerary.data.OkHttpItineraryApi
import com.kltn.travelassistant.feature.itinerary.data.OkHttpSavedItineraryApi
import com.kltn.travelassistant.feature.itinerary.data.RoomSavedItineraryRepository
import com.kltn.travelassistant.feature.itinerary.data.SavedItineraryApi
import com.kltn.travelassistant.feature.itinerary.data.SavedItineraryLocalCodec
import com.kltn.travelassistant.feature.itinerary.data.SavedItineraryNetworkCodec
import com.kltn.travelassistant.feature.itinerary.data.WorkManagerItineraryScheduler
import com.kltn.travelassistant.feature.itinerary.domain.ItineraryDraftGenerator
import com.kltn.travelassistant.feature.itinerary.domain.ItinerarySaveBoundary
import com.kltn.travelassistant.feature.itinerary.domain.SavedItineraryRepository
import dagger.Binds
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.components.SingletonComponent
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
internal abstract class ItineraryModule {
    @Binds
    @Singleton
    abstract fun bindItineraryDraftGenerator(
        implementation: DefaultItineraryDraftGenerator,
    ): ItineraryDraftGenerator

    @Binds
    @Singleton
    abstract fun bindItineraryHttpApi(
        implementation: OkHttpItineraryApi,
    ): ItineraryHttpApi

    @Binds
    @Singleton
    abstract fun bindItinerarySaveBoundary(
        implementation: RoomSavedItineraryRepository,
    ): ItinerarySaveBoundary

    @Binds
    @Singleton
    abstract fun bindSavedItineraryRepository(
        implementation: RoomSavedItineraryRepository,
    ): SavedItineraryRepository

    @Binds
    @Singleton
    abstract fun bindSavedItineraryApi(
        implementation: OkHttpSavedItineraryApi,
    ): SavedItineraryApi

    @Binds
    @Singleton
    abstract fun bindItineraryWorkScheduler(
        implementation: WorkManagerItineraryScheduler,
    ): ItineraryWorkScheduler

    companion object {
        @Provides
        @Singleton
        fun provideSavedItineraryLocalCodec(): SavedItineraryLocalCodec =
            SavedItineraryLocalCodec()

        @Provides
        @Singleton
        fun provideSavedItineraryNetworkCodec(): SavedItineraryNetworkCodec =
            SavedItineraryNetworkCodec()
    }
}
