package com.kltn.travelassistant.di

import com.kltn.travelassistant.feature.itinerary.data.UnavailableItinerarySaveBoundary
import com.kltn.travelassistant.feature.itinerary.data.UnsupportedTransportItineraryDraftGenerator
import com.kltn.travelassistant.feature.itinerary.domain.ItineraryDraftGenerator
import com.kltn.travelassistant.feature.itinerary.domain.ItinerarySaveBoundary
import dagger.Binds
import dagger.Module
import dagger.hilt.InstallIn
import dagger.hilt.components.SingletonComponent
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
internal abstract class ItineraryModule {
    @Binds
    @Singleton
    abstract fun bindItineraryDraftGenerator(
        implementation: UnsupportedTransportItineraryDraftGenerator,
    ): ItineraryDraftGenerator

    @Binds
    @Singleton
    abstract fun bindItinerarySaveBoundary(
        implementation: UnavailableItinerarySaveBoundary,
    ): ItinerarySaveBoundary
}
