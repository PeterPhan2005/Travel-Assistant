package com.kltn.travelassistant.feature.downloads.presentation

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.kltn.travelassistant.feature.downloads.domain.PackageSyncRepository
import com.kltn.travelassistant.feature.downloads.domain.PackageWorkState
import dagger.hilt.android.lifecycle.HiltViewModel
import javax.inject.Inject
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.catch
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.flow.stateIn

@HiltViewModel
class DownloadsViewModel @Inject constructor(
    private val repository: PackageSyncRepository,
) : ViewModel() {
    val uiState = repository.observeHcmcSync()
        .map { state ->
            DownloadsUiState(
                isLoading = false,
                activePackage = state.activePackage,
                status = when (val workState = state.workState) {
                    PackageWorkState.Idle -> DownloadsStatus.Idle
                    is PackageWorkState.Running -> DownloadsStatus.InProgress(workState.phase)
                    PackageWorkState.Succeeded -> DownloadsStatus.Success
                    is PackageWorkState.Failed -> DownloadsStatus.Failure(workState.code)
                },
            )
        }
        .catch {
            emit(
                DownloadsUiState(
                    isLoading = false,
                    status = DownloadsStatus.Failure(
                        com.kltn.travelassistant.feature.downloads.domain
                            .PackageSyncFailureCode.ACTIVATION_FAILED,
                    ),
                ),
            )
        }
        .stateIn(
            scope = viewModelScope,
            started = SharingStarted.Eagerly,
            initialValue = DownloadsUiState(),
        )

    fun download() {
        repository.startHcmcDownload()
    }

    fun retry() {
        repository.retryHcmcDownload()
    }
}
