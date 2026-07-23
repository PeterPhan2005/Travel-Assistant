package com.kltn.travelassistant.feature.appshell.domain

import kotlinx.coroutines.flow.Flow

data class LocalTravelPackageMetadata(
    val version: String,
    val publishedAtEpochMillis: Long,
)

interface LocalTravelPackageRepository {
    fun observeLatestHcmcPackage(): Flow<LocalTravelPackageMetadata?>
}
