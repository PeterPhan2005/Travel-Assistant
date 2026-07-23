package com.kltn.travelassistant.feature.appshell.presentation

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.kltn.travelassistant.data.connectivity.ConnectivityObserver
import com.kltn.travelassistant.data.connectivity.ConnectivityStatus
import com.kltn.travelassistant.feature.appshell.domain.LocalTravelPackageRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import javax.inject.Inject
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.catch
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.flow.onStart
import kotlinx.coroutines.flow.onEach
import kotlinx.coroutines.flow.stateIn

@HiltViewModel
class AppShellViewModel @Inject constructor(
    connectivityObserver: ConnectivityObserver,
    localTravelPackageRepository: LocalTravelPackageRepository,
) : ViewModel() {
    private val mutableOfflineWarningDismissed = MutableStateFlow(false)

    private val connectivityState = connectivityObserver.status
        .map(ConnectivityStatus::toUiState)
        .onStart { emit(ConnectivityUiState.Checking) }
        .catch { emit(ConnectivityUiState.Checking) }
        .onEach { connectivity ->
            if (connectivity != ConnectivityUiState.Offline) {
                mutableOfflineWarningDismissed.value = false
            }
        }

    private val packageState = localTravelPackageRepository.observeLatestHcmcPackage()
        .map { metadata ->
            if (metadata == null || metadata.version.isBlank()) {
                LocalPackageUiState.Unavailable
            } else {
                LocalPackageUiState.Available(
                    version = metadata.version,
                    publishedAtEpochMillis = metadata.publishedAtEpochMillis,
                )
            }
        }
        .onStart { emit(LocalPackageUiState.Loading) }
        .catch { emit(LocalPackageUiState.Error) }

    val uiState = combine(
        connectivityState,
        packageState,
        mutableOfflineWarningDismissed,
    ) { connectivity, localPackage, isOfflineWarningDismissed ->
        AppShellUiState(
            connectivity = connectivity,
            localPackage = localPackage,
            isOfflineWarningDismissed = connectivity == ConnectivityUiState.Offline &&
                isOfflineWarningDismissed,
        )
    }
        .stateIn(
            scope = viewModelScope,
            started = SharingStarted.Eagerly,
            initialValue = AppShellUiState(),
        )

    fun dismissOfflineWarning() {
        if (uiState.value.connectivity == ConnectivityUiState.Offline) {
            mutableOfflineWarningDismissed.value = true
        }
    }
}

private fun ConnectivityStatus.toUiState(): ConnectivityUiState = when (this) {
    ConnectivityStatus.UNKNOWN -> ConnectivityUiState.Checking
    ConnectivityStatus.ONLINE -> ConnectivityUiState.Online
    ConnectivityStatus.OFFLINE -> ConnectivityUiState.Offline
}
