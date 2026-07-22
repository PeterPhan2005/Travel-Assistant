package com.kltn.travelassistant.navigation

import androidx.compose.material3.Icon
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.res.stringResource
import androidx.navigation.NavGraph.Companion.findStartDestination
import androidx.navigation.NavHostController
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import com.kltn.travelassistant.R
import com.kltn.travelassistant.feature.home.presentation.HomeScreen
import com.kltn.travelassistant.feature.home.presentation.HomeUiState

@Composable
fun TravelAssistantNavigationBar(
    destinations: List<TopLevelDestination>,
    selectedDestination: TopLevelDestination?,
    onDestinationSelected: (TopLevelDestination) -> Unit,
    modifier: Modifier = Modifier,
) {
    NavigationBar(modifier = modifier) {
        destinations.forEach { destination ->
            NavigationBarItem(
                selected = destination == selectedDestination,
                onClick = { onDestinationSelected(destination) },
                icon = {
                    Icon(
                        imageVector = destination.icon,
                        contentDescription = stringResource(destination.iconContentDescriptionRes),
                    )
                },
                label = { Text(text = stringResource(destination.labelRes)) },
                modifier = Modifier.testTag(navigationItemTestTag(destination)),
            )
        }
    }
}

@Composable
fun TravelAssistantNavHost(
    navController: NavHostController,
    homeUiState: HomeUiState,
    onUseCurrentLocation: () -> Unit,
    onOpenLocationSettings: () -> Unit,
    modifier: Modifier = Modifier,
) {
    NavHost(
        navController = navController,
        startDestination = TopLevelDestination.startDestination.route,
        modifier = modifier,
    ) {
        composable(TopLevelDestination.EXPLORE.route) {
            HomeScreen(
                uiState = homeUiState,
                onUseCurrentLocation = onUseCurrentLocation,
                onOpenLocationSettings = onOpenLocationSettings,
            )
        }
        composable(TopLevelDestination.ASSISTANT.route) {
            PlaceholderDestinationScreen(titleRes = R.string.destination_assistant)
        }
        composable(TopLevelDestination.ITINERARY.route) {
            PlaceholderDestinationScreen(titleRes = R.string.destination_itinerary)
        }
        composable(TopLevelDestination.DOWNLOADS.route) {
            PlaceholderDestinationScreen(titleRes = R.string.destination_downloads)
        }
        composable(TopLevelDestination.PROFILE.route) {
            PlaceholderDestinationScreen(titleRes = R.string.destination_profile)
        }
    }
}

fun NavHostController.navigateToTopLevelDestination(destination: TopLevelDestination) {
    navigate(destination.route) {
        popUpTo(graph.findStartDestination().id) {
            saveState = true
        }
        launchSingleTop = true
        restoreState = true
    }
}

fun navigationItemTestTag(destination: TopLevelDestination): String =
    "top-level-${destination.route}"
