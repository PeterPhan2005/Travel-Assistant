package com.kltn.travelassistant.data.repository

import com.kltn.travelassistant.data.packages.PackageWorkScheduler
import com.kltn.travelassistant.feature.appshell.domain.LocalTravelPackageRepository
import com.kltn.travelassistant.feature.downloads.domain.ActivePackageMetadata
import com.kltn.travelassistant.feature.downloads.domain.PackageCity
import com.kltn.travelassistant.feature.downloads.domain.PackageSyncRepository
import com.kltn.travelassistant.feature.downloads.domain.PackageSyncState
import com.kltn.travelassistant.feature.downloads.domain.PackageWorkState
import javax.inject.Inject
import javax.inject.Singleton
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.catch
import kotlinx.coroutines.flow.combine

@Singleton
class DefaultPackageSyncRepository @Inject constructor(
    private val scheduler: PackageWorkScheduler,
    private val localPackages: LocalTravelPackageRepository,
) : PackageSyncRepository {
    override fun observeHcmcSync(): Flow<PackageSyncState> = combine(
        localPackages.observeLatestHcmcPackage(),
        scheduler.observe(PackageCity.HCMC)
            .catch { emit(PackageWorkState.Idle) },
    ) { activePackage, workState ->
        PackageSyncState(
            activePackage = activePackage?.let {
                ActivePackageMetadata(
                    packageId = it.packageId,
                    city = PackageCity.HCMC,
                    contentVersion = it.version,
                    publishedAtEpochMillis = it.publishedAtEpochMillis,
                    origin = it.origin,
                )
            },
            workState = workState,
        )
    }

    override fun startHcmcDownload() {
        scheduler.enqueue(PackageCity.HCMC, replace = false)
    }

    override fun retryHcmcDownload() {
        scheduler.enqueue(PackageCity.HCMC, replace = true)
    }
}
