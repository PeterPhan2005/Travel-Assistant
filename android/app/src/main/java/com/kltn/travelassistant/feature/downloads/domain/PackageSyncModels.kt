package com.kltn.travelassistant.feature.downloads.domain

import kotlinx.coroutines.flow.Flow

enum class PackageCity(
    val code: String,
    val displayName: String,
    val packageId: String,
) {
    HCMC(
        code = "hcmc",
        displayName = "Ho Chi Minh City",
        packageId = "hcmc-starter-v1",
    ),
}

enum class PackageOrigin {
    BUNDLED,
    DOWNLOADED,
}

data class ActivePackageMetadata(
    val packageId: String,
    val city: PackageCity,
    val contentVersion: String,
    val publishedAtEpochMillis: Long,
    val origin: PackageOrigin,
)

enum class PackageSyncPhase {
    QUEUED,
    DOWNLOADING_MANIFEST,
    DOWNLOADING_DATA,
    VERIFYING,
    VALIDATING,
    ACTIVATING,
}

enum class PackageSyncFailureCode(val retryable: Boolean) {
    NETWORK_UNAVAILABLE(true),
    TEMPORARY_SERVER_FAILURE(true),
    INVALID_MANIFEST(false),
    UNSUPPORTED_PACKAGE(false),
    CHECKSUM_MISMATCH(false),
    INVALID_DATA(false),
    ACTIVATION_FAILED(false),
    CANCELLED(true),
}

sealed interface PackageWorkState {
    data object Idle : PackageWorkState

    data class Running(val phase: PackageSyncPhase) : PackageWorkState

    data object Succeeded : PackageWorkState

    data class Failed(val code: PackageSyncFailureCode) : PackageWorkState
}

data class PackageSyncState(
    val activePackage: ActivePackageMetadata? = null,
    val workState: PackageWorkState = PackageWorkState.Idle,
)

interface PackageSyncRepository {
    fun observeHcmcSync(): Flow<PackageSyncState>

    fun startHcmcDownload()

    fun retryHcmcDownload()
}
