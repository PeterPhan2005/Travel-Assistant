package com.kltn.travelassistant.di

import com.kltn.travelassistant.data.connectivity.AndroidConnectivityManagerGateway
import com.kltn.travelassistant.data.connectivity.ConnectivityManagerGateway
import com.kltn.travelassistant.data.connectivity.ConnectivityObserver
import com.kltn.travelassistant.data.connectivity.DefaultConnectivityObserver
import dagger.Binds
import dagger.Module
import dagger.hilt.InstallIn
import dagger.hilt.components.SingletonComponent
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
internal abstract class ConnectivityModule {
    @Binds
    @Singleton
    abstract fun bindConnectivityManagerGateway(
        implementation: AndroidConnectivityManagerGateway,
    ): ConnectivityManagerGateway

    @Binds
    @Singleton
    abstract fun bindConnectivityObserver(
        implementation: DefaultConnectivityObserver,
    ): ConnectivityObserver
}
