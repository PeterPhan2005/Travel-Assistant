package com.kltn.travelassistant.di

import com.kltn.travelassistant.navigation.external.AndroidExternalNavigationLauncher
import com.kltn.travelassistant.navigation.external.AndroidExternalMapActivityGateway
import com.kltn.travelassistant.navigation.external.ExternalNavigationAnalytics
import com.kltn.travelassistant.navigation.external.ExternalNavigationLauncher
import com.kltn.travelassistant.navigation.external.ExternalMapActivityGateway
import com.kltn.travelassistant.navigation.external.NoOpExternalNavigationAnalytics
import dagger.Binds
import dagger.Module
import dagger.hilt.InstallIn
import dagger.hilt.components.SingletonComponent
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
abstract class ExternalNavigationModule {
    @Binds
    @Singleton
    abstract fun bindExternalNavigationLauncher(
        implementation: AndroidExternalNavigationLauncher,
    ): ExternalNavigationLauncher

    @Binds
    @Singleton
    abstract fun bindExternalMapActivityGateway(
        implementation: AndroidExternalMapActivityGateway,
    ): ExternalMapActivityGateway

    @Binds
    @Singleton
    abstract fun bindExternalNavigationAnalytics(
        implementation: NoOpExternalNavigationAnalytics,
    ): ExternalNavigationAnalytics
}
