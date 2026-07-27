package com.kltn.travelassistant.data.repository

import com.kltn.travelassistant.data.local.dao.TravelPackageDao
import com.kltn.travelassistant.feature.appshell.domain.LocalTravelPackageMetadata
import com.kltn.travelassistant.feature.appshell.domain.LocalTravelPackageRepository
import com.kltn.travelassistant.feature.downloads.domain.PackageOrigin
import javax.inject.Inject
import javax.inject.Singleton
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map

@Singleton
class RoomLocalTravelPackageRepository @Inject constructor(
    private val travelPackageDao: TravelPackageDao,
) : LocalTravelPackageRepository {
    override fun observeLatestHcmcPackage(): Flow<LocalTravelPackageMetadata?> =
        travelPackageDao.observeLatestPackage(HO_CHI_MINH_CITY)
            .map { entity ->
                entity?.let {
                    LocalTravelPackageMetadata(
                        packageId = it.packageId,
                        version = it.version,
                        publishedAtEpochMillis = it.publishedAtEpochMillis,
                        origin = if (it.packageId == BUNDLED_PACKAGE_ID) {
                            PackageOrigin.BUNDLED
                        } else {
                            PackageOrigin.DOWNLOADED
                        },
                    )
                }
            }

    private companion object {
        const val HO_CHI_MINH_CITY = "Ho Chi Minh City"
        const val BUNDLED_PACKAGE_ID = "bundled-hcmc-demo"
    }
}
