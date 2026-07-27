package com.kltn.travelassistant.di

import com.kltn.travelassistant.data.packages.BuildConfigPackageManifestLocationProvider
import com.kltn.travelassistant.data.packages.PackageActivator
import com.kltn.travelassistant.data.packages.PackageManifestLocationProvider
import com.kltn.travelassistant.data.packages.RoomPackageActivator
import com.kltn.travelassistant.data.packages.PackageWorkScheduler
import com.kltn.travelassistant.data.packages.WorkManagerPackageScheduler
import dagger.Binds
import dagger.Module
import dagger.hilt.InstallIn
import dagger.hilt.components.SingletonComponent
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
abstract class PackageSyncModule {
    @Binds
    @Singleton
    abstract fun bindManifestLocationProvider(
        provider: BuildConfigPackageManifestLocationProvider,
    ): PackageManifestLocationProvider

    @Binds
    @Singleton
    abstract fun bindPackageActivator(activator: RoomPackageActivator): PackageActivator

    @Binds
    @Singleton
    abstract fun bindPackageWorkScheduler(
        scheduler: WorkManagerPackageScheduler,
    ): PackageWorkScheduler
}
