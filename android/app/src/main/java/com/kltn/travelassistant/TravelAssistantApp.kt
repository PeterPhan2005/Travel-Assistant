package com.kltn.travelassistant

import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Scaffold
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import com.kltn.travelassistant.feature.home.presentation.HomeViewModel
import com.kltn.travelassistant.feature.home.presentation.HomeUiState
import com.kltn.travelassistant.feature.poi.presentation.PoiDetailRoute
import com.kltn.travelassistant.navigation.TopLevelDestination
import com.kltn.travelassistant.navigation.TravelAssistantNavHost
import com.kltn.travelassistant.navigation.TravelAssistantNavigationBar
import com.kltn.travelassistant.navigation.navigateToTopLevelDestination
import com.kltn.travelassistant.ui.theme.TravelAssistantTheme

@Composable
fun TravelAssistantApp(
    homeViewModel: HomeViewModel,
    onUseCurrentLocation: () -> Unit,
    onOpenLocationSettings: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val uiState by homeViewModel.uiState.collectAsStateWithLifecycle()
    TravelAssistantAppContent(
        homeUiState = uiState,
        onUseCurrentLocation = onUseCurrentLocation,
        onOpenLocationSettings = onOpenLocationSettings,
        onNearbyQueryChanged = homeViewModel::onNearbyQueryChanged,
        modifier = modifier,
    )
}

@Composable
fun TravelAssistantAppContent(
    homeUiState: HomeUiState,
    onUseCurrentLocation: () -> Unit,
    onOpenLocationSettings: () -> Unit,
    onNearbyQueryChanged: (String) -> Unit,
    modifier: Modifier = Modifier,
    poiDetailContent: @Composable (poiId: String, onBack: () -> Unit) -> Unit = { _, onBack ->
        PoiDetailRoute(onBack = onBack)
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
            TravelAssistantNavHost(
                navController = navController,
                homeUiState = homeUiState,
                onUseCurrentLocation = onUseCurrentLocation,
                onOpenLocationSettings = onOpenLocationSettings,
                onNearbyQueryChanged = onNearbyQueryChanged,
                poiDetailContent = poiDetailContent,
                modifier = Modifier.padding(innerPadding),
            )
        }
    }
}
