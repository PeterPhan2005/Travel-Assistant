package com.kltn.travelassistant.feature.appshell.domain

import com.kltn.travelassistant.feature.downloads.domain.PackageOrigin
import kotlinx.coroutines.flow.Flow

data class LocalTravelPackageMetadata(
    val packageId: String,
    val version: String,
    val publishedAtEpochMillis: Long,
    val origin: PackageOrigin,
)

interface LocalTravelPackageRepository {
    fun observeLatestHcmcPackage(): Flow<LocalTravelPackageMetadata?>
}
