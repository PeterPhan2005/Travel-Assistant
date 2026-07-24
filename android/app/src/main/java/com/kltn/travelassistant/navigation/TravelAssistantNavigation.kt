package com.kltn.travelassistant.navigation

import android.net.Uri
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
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.navArgument
import com.kltn.travelassistant.R
import com.kltn.travelassistant.feature.appshell.presentation.ConnectivityUiState
import com.kltn.travelassistant.feature.appshell.presentation.LocalPackageMetadataSection
import com.kltn.travelassistant.feature.appshell.presentation.LocalPackageUiState
import com.kltn.travelassistant.feature.auth.presentation.AuthFormMode
import com.kltn.travelassistant.feature.auth.presentation.ProfileScreen
import com.kltn.travelassistant.feature.auth.presentation.ProfileUiState
import com.kltn.travelassistant.feature.home.presentation.HomeScreen
import com.kltn.travelassistant.feature.home.presentation.HomeUiState
import com.kltn.travelassistant.feature.poi.domain.PoiNavigationTarget
import com.kltn.travelassistant.feature.poi.presentation.PoiDetailRoute
import com.kltn.travelassistant.navigation.external.ExternalNavigationResult

object PoiDetailDestination {
    const val POI_ID_ARGUMENT = "poiId"
    const val ROUTE_PATTERN = "poi/{$POI_ID_ARGUMENT}"

    fun createRoute(poiId: String): String {
        require(poiId.isNotBlank())
        return "poi/${Uri.encode(poiId)}"
    }
}

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
    profileUiState: ProfileUiState = ProfileUiState(),
    connectivityUiState: ConnectivityUiState = ConnectivityUiState.Checking,
    localPackageUiState: LocalPackageUiState = LocalPackageUiState.Loading,
    onUseCurrentLocation: () -> Unit,
    onOpenLocationSettings: () -> Unit,
    onNearbyQueryChanged: (String) -> Unit,
    onAuthFormModeChanged: (AuthFormMode) -> Unit = {},
    onAuthEmailChanged: (String) -> Unit = {},
    onAuthPasswordChanged: (String) -> Unit = {},
    onAuthPasswordConfirmationChanged: (String) -> Unit = {},
    onAuthSubmit: () -> Unit = {},
    onAuthRefreshVerification: () -> Unit = {},
    onAuthResendVerificationEmail: () -> Unit = {},
    onAuthSignOut: () -> Unit = {},
    onAuthRetrySession: () -> Unit = {},
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
                onNearbyQueryChanged = onNearbyQueryChanged,
                onPoiSelected = { poiId ->
                    navController.navigate(PoiDetailDestination.createRoute(poiId)) {
                        launchSingleTop = true
                    }
                },
            )
        }
        composable(TopLevelDestination.ASSISTANT.route) {
            PlaceholderDestinationScreen(
                titleRes = R.string.destination_assistant,
                unavailableExplanationRes = if (
                    connectivityUiState == ConnectivityUiState.Offline
                ) {
                    R.string.assistant_offline_explanation
                } else {
                    null
                },
            )
        }
        composable(TopLevelDestination.ITINERARY.route) {
            PlaceholderDestinationScreen(titleRes = R.string.destination_itinerary)
        }
        composable(TopLevelDestination.DOWNLOADS.route) {
            PlaceholderDestinationScreen(
                titleRes = R.string.destination_downloads,
                unavailableExplanationRes = if (
                    connectivityUiState == ConnectivityUiState.Offline
                ) {
                    R.string.downloads_offline_explanation
                } else {
                    null
                },
                additionalContent = {
                    LocalPackageMetadataSection(uiState = localPackageUiState)
                },
            )
        }
        composable(TopLevelDestination.PROFILE.route) {
            ProfileScreen(
                uiState = profileUiState,
                onFormModeChanged = onAuthFormModeChanged,
                onEmailChanged = onAuthEmailChanged,
                onPasswordChanged = onAuthPasswordChanged,
                onPasswordConfirmationChanged = onAuthPasswordConfirmationChanged,
                onSubmit = onAuthSubmit,
                onRefreshVerification = onAuthRefreshVerification,
                onResendVerificationEmail = onAuthResendVerificationEmail,
                onSignOut = onAuthSignOut,
                onRetrySession = onAuthRetrySession,
            )
        }
        composable(
            route = PoiDetailDestination.ROUTE_PATTERN,
            arguments = listOf(
                navArgument(PoiDetailDestination.POI_ID_ARGUMENT) {
                    type = NavType.StringType
                },
            ),
        ) { backStackEntry ->
            val poiId = backStackEntry.arguments
                ?.getString(PoiDetailDestination.POI_ID_ARGUMENT)
                .orEmpty()
            poiDetailContent(poiId) { navController.popBackStack() }
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
