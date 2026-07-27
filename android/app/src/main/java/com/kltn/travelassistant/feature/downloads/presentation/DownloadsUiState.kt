package com.kltn.travelassistant.feature.downloads.presentation

import com.kltn.travelassistant.feature.downloads.domain.ActivePackageMetadata
import com.kltn.travelassistant.feature.downloads.domain.PackageSyncFailureCode
import com.kltn.travelassistant.feature.downloads.domain.PackageSyncPhase

data class DownloadsUiState(
    val isLoading: Boolean = true,
    val activePackage: ActivePackageMetadata? = null,
    val status: DownloadsStatus = DownloadsStatus.Idle,
)

sealed interface DownloadsStatus {
    data object Idle : DownloadsStatus

    data class InProgress(val phase: PackageSyncPhase) : DownloadsStatus

    data object Success : DownloadsStatus

    data class Failure(val code: PackageSyncFailureCode) : DownloadsStatus
}
