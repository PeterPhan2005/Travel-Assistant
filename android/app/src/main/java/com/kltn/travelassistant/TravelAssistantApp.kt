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
import com.kltn.travelassistant.feature.home.presentation.HomeViewModel
import com.kltn.travelassistant.feature.home.presentation.HomeUiState
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
    onUseCurrentLocation: () -> Unit,
    onOpenLocationSettings: () -> Unit,
    onOpenExternalNavigation: (PoiNavigationTarget) -> ExternalNavigationResult,
    modifier: Modifier = Modifier,
) {
    val appShellUiState by appShellViewModel.uiState.collectAsStateWithLifecycle()
    val homeUiState by homeViewModel.uiState.collectAsStateWithLifecycle()
    TravelAssistantAppContent(
        appShellUiState = appShellUiState,
        homeUiState = homeUiState,
        onUseCurrentLocation = onUseCurrentLocation,
        onOpenLocationSettings = onOpenLocationSettings,
        onNearbyQueryChanged = homeViewModel::onNearbyQueryChanged,
        onDismissOfflineWarning = appShellViewModel::dismissOfflineWarning,
        onOpenExternalNavigation = onOpenExternalNavigation,
        modifier = modifier,
    )
}

@Composable
fun TravelAssistantAppContent(
    homeUiState: HomeUiState,
    appShellUiState: AppShellUiState = AppShellUiState(),
    onUseCurrentLocation: () -> Unit,
    onOpenLocationSettings: () -> Unit,
    onNearbyQueryChanged: (String) -> Unit,
    onDismissOfflineWarning: () -> Unit = {},
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
                    connectivityUiState = appShellUiState.connectivity,
                    localPackageUiState = appShellUiState.localPackage,
                    onUseCurrentLocation = onUseCurrentLocation,
                    onOpenLocationSettings = onOpenLocationSettings,
                    onNearbyQueryChanged = onNearbyQueryChanged,
                    onOpenExternalNavigation = onOpenExternalNavigation,
                    poiDetailContent = poiDetailContent,
                    modifier = Modifier.weight(1f),
                )
            }
        }
    }
}
