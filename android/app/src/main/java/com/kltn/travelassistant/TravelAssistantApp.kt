package com.kltn.travelassistant

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Scaffold
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import com.kltn.travelassistant.feature.appshell.presentation.AppShellStatusPresentation
import com.kltn.travelassistant.feature.appshell.presentation.AppShellUiState
import com.kltn.travelassistant.feature.appshell.presentation.AppShellViewModel
import com.kltn.travelassistant.feature.auth.presentation.AuthFormMode
import com.kltn.travelassistant.feature.auth.presentation.ProfileUiState
import com.kltn.travelassistant.feature.auth.presentation.ProfileViewModel
import com.kltn.travelassistant.feature.home.presentation.HomeViewModel
import com.kltn.travelassistant.feature.home.presentation.HomeUiState
import com.kltn.travelassistant.feature.downloads.presentation.DownloadsUiState
import com.kltn.travelassistant.feature.downloads.presentation.DownloadsViewModel
import com.kltn.travelassistant.feature.poi.domain.PoiNavigationTarget
import com.kltn.travelassistant.feature.poi.presentation.PoiDetailRoute
import com.kltn.travelassistant.navigation.TopLevelDestination
import com.kltn.travelassistant.navigation.TravelAssistantNavHost
import com.kltn.travelassistant.navigation.TravelAssistantNavigationBar
import com.kltn.travelassistant.navigation.external.ExternalNavigationResult
import com.kltn.travelassistant.navigation.navigateToTopLevelDestination
import com.kltn.travelassistant.ui.theme.TravelAssistantTheme

@Composable
fun TravelAssistantApp(
    appShellViewModel: AppShellViewModel,
    homeViewModel: HomeViewModel,
    profileViewModel: ProfileViewModel,
    downloadsViewModel: DownloadsViewModel,
    onUseCurrentLocation: () -> Unit,
    onOpenLocationSettings: () -> Unit,
    onOpenExternalNavigation: (PoiNavigationTarget) -> ExternalNavigationResult,
    onGoogleSignIn: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val appShellUiState by appShellViewModel.uiState.collectAsStateWithLifecycle()
    val homeUiState by homeViewModel.uiState.collectAsStateWithLifecycle()
    val profileUiState by profileViewModel.uiState.collectAsStateWithLifecycle()
    val downloadsUiState by downloadsViewModel.uiState.collectAsStateWithLifecycle()
    TravelAssistantAppContent(
        appShellUiState = appShellUiState,
        homeUiState = homeUiState,
        profileUiState = profileUiState,
        downloadsUiState = downloadsUiState,
        onUseCurrentLocation = onUseCurrentLocation,
        onOpenLocationSettings = onOpenLocationSettings,
        onNearbyQueryChanged = homeViewModel::onNearbyQueryChanged,
        onAuthFormModeChanged = profileViewModel::onFormModeChanged,
        onAuthEmailChanged = profileViewModel::onEmailChanged,
        onAuthPasswordChanged = profileViewModel::onPasswordChanged,
        onAuthPasswordConfirmationChanged = profileViewModel::onPasswordConfirmationChanged,
        onAuthSubmit = profileViewModel::submit,
        onGoogleSignIn = onGoogleSignIn,
        onAuthRefreshVerification = profileViewModel::refreshVerification,
        onAuthResendVerificationEmail = profileViewModel::resendVerificationEmail,
        onAuthSignOut = profileViewModel::signOut,
        onAuthRetrySession = profileViewModel::retrySessionObservation,
        onDismissOfflineWarning = appShellViewModel::dismissOfflineWarning,
        onDownloadPackage = downloadsViewModel::download,
        onRetryPackageDownload = downloadsViewModel::retry,
        onOpenExternalNavigation = onOpenExternalNavigation,
        modifier = modifier,
    )
}

@Composable
fun TravelAssistantAppContent(
    homeUiState: HomeUiState,
    appShellUiState: AppShellUiState = AppShellUiState(),
    profileUiState: ProfileUiState = ProfileUiState(),
    downloadsUiState: DownloadsUiState? = null,
    onUseCurrentLocation: () -> Unit,
    onOpenLocationSettings: () -> Unit,
    onNearbyQueryChanged: (String) -> Unit,
    onAuthFormModeChanged: (AuthFormMode) -> Unit = {},
    onAuthEmailChanged: (String) -> Unit = {},
    onAuthPasswordChanged: (String) -> Unit = {},
    onAuthPasswordConfirmationChanged: (String) -> Unit = {},
    onAuthSubmit: () -> Unit = {},
    onGoogleSignIn: () -> Unit = {},
    onAuthRefreshVerification: () -> Unit = {},
    onAuthResendVerificationEmail: () -> Unit = {},
    onAuthSignOut: () -> Unit = {},
    onAuthRetrySession: () -> Unit = {},
    onDismissOfflineWarning: () -> Unit = {},
    onDownloadPackage: () -> Unit = {},
    onRetryPackageDownload: () -> Unit = {},
    modifier: Modifier = Modifier,
    onOpenExternalNavigation: (PoiNavigationTarget) -> ExternalNavigationResult = {
        ExternalNavigationResult.LaunchFailed
    },
    poiDetailContent: @Composable (poiId: String, onBack: () -> Unit) -> Unit = { _, onBack ->
        PoiDetailRoute(
            onBack = onBack,
            onOpenExternalNavigation = onOpenExternalNavigation,
        )
    },
) {
    val navController = rememberNavController()
    val navBackStackEntry by navController.currentBackStackEntryAsState()
    val selectedDestination = TopLevelDestination.fromRoute(
        route = navBackStackEntry?.destination?.route,
    )

    TravelAssistantTheme {
        Scaffold(
            modifier = modifier.fillMaxSize(),
            bottomBar = {
                selectedDestination?.let {
                    TravelAssistantNavigationBar(
                        destinations = TopLevelDestination.all,
                        selectedDestination = selectedDestination,
                        onDestinationSelected = navController::navigateToTopLevelDestination,
                    )
                }
            },
        ) { innerPadding ->
            Column(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(innerPadding),
            ) {
                AppShellStatusPresentation(
                    connectivityUiState = appShellUiState.connectivity,
                    shouldShowOfflineWarning = appShellUiState.shouldShowOfflineWarning,
                    onDismissOfflineWarning = onDismissOfflineWarning,
                )
                TravelAssistantNavHost(
                    navController = navController,
                    homeUiState = homeUiState,
                    profileUiState = profileUiState,
                    connectivityUiState = appShellUiState.connectivity,
                    localPackageUiState = appShellUiState.localPackage,
                    downloadsUiState = downloadsUiState,
                    onUseCurrentLocation = onUseCurrentLocation,
                    onOpenLocationSettings = onOpenLocationSettings,
                    onNearbyQueryChanged = onNearbyQueryChanged,
                    onAuthFormModeChanged = onAuthFormModeChanged,
                    onAuthEmailChanged = onAuthEmailChanged,
                    onAuthPasswordChanged = onAuthPasswordChanged,
                    onAuthPasswordConfirmationChanged = onAuthPasswordConfirmationChanged,
                    onAuthSubmit = onAuthSubmit,
                    onGoogleSignIn = onGoogleSignIn,
                    onAuthRefreshVerification = onAuthRefreshVerification,
                    onAuthResendVerificationEmail = onAuthResendVerificationEmail,
                    onAuthSignOut = onAuthSignOut,
                    onAuthRetrySession = onAuthRetrySession,
                    onDownloadPackage = onDownloadPackage,
                    onRetryPackageDownload = onRetryPackageDownload,
                    onOpenExternalNavigation = onOpenExternalNavigation,
                    poiDetailContent = poiDetailContent,
                    modifier = Modifier.weight(1f),
                )
            }
        }
    }
}
