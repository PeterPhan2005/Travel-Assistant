package com.kltn.travelassistant.feature.appshell.presentation

data class AppShellUiState(
    val connectivity: ConnectivityUiState = ConnectivityUiState.Checking,
    val localPackage: LocalPackageUiState = LocalPackageUiState.Loading,
    val isOfflineWarningDismissed: Boolean = false,
) {
    val shouldShowOfflineWarning: Boolean
        get() = connectivity == ConnectivityUiState.Offline && !isOfflineWarningDismissed
}

enum class ConnectivityUiState {
    Checking,
    Online,
    Offline,
}

sealed interface LocalPackageUiState {
    data object Loading : LocalPackageUiState

    data class Available(
        val version: String,
        val publishedAtEpochMillis: Long,
    ) : LocalPackageUiState

    data object Unavailable : LocalPackageUiState

    data object Error : LocalPackageUiState
}
