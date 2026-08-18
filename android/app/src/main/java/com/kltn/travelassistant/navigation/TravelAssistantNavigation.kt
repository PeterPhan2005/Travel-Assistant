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
import com.kltn.travelassistant.feature.assistant.presentation.AssistantScreen
import com.kltn.travelassistant.feature.assistant.presentation.AssistantUiState
import com.kltn.travelassistant.feature.auth.presentation.AuthFormMode
import com.kltn.travelassistant.feature.auth.presentation.ProfileScreen
import com.kltn.travelassistant.feature.auth.presentation.ProfileUiState
import com.kltn.travelassistant.feature.home.presentation.HomeScreen
import com.kltn.travelassistant.feature.home.presentation.HomeUiState
import com.kltn.travelassistant.feature.itinerary.domain.ItineraryCity
import com.kltn.travelassistant.feature.itinerary.presentation.ItineraryScreen
import com.kltn.travelassistant.feature.itinerary.presentation.ItineraryUiState
import com.kltn.travelassistant.feature.downloads.domain.ActivePackageMetadata
import com.kltn.travelassistant.feature.downloads.domain.PackageCity
import com.kltn.travelassistant.feature.downloads.domain.PackageOrigin
import com.kltn.travelassistant.feature.downloads.presentation.DownloadsScreen
import com.kltn.travelassistant.feature.downloads.presentation.DownloadsStatus
import com.kltn.travelassistant.feature.downloads.presentation.DownloadsUiState
import com.kltn.travelassistant.feature.poi.domain.PoiNavigationTarget
import com.kltn.travelassistant.feature.poi.presentation.PoiDetailRoute
import com.kltn.travelassistant.feature.preferences.domain.BudgetPreference
import com.kltn.travelassistant.feature.preferences.domain.TravelInterest
import com.kltn.travelassistant.feature.preferences.domain.TravelPace
import com.kltn.travelassistant.feature.preferences.presentation.PreferenceProfileUiState
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
internal fun TravelAssistantNavHost(
    navController: NavHostController,
    homeUiState: HomeUiState,
    assistantUiState: AssistantUiState = AssistantUiState(),
    itineraryUiState: ItineraryUiState = ItineraryUiState(),
    profileUiState: ProfileUiState = ProfileUiState(),
    preferenceProfileUiState: PreferenceProfileUiState = PreferenceProfileUiState(),
    connectivityUiState: ConnectivityUiState = ConnectivityUiState.Checking,
    localPackageUiState: LocalPackageUiState = LocalPackageUiState.Loading,
    downloadsUiState: DownloadsUiState? = null,
    onUseCurrentLocation: () -> Unit,
    onOpenLocationSettings: () -> Unit,
    onNearbyQueryChanged: (String) -> Unit,
    onDemoLocationPresetSelected: (String) -> Unit = {},
    onAssistantQueryChanged: (String) -> Unit = {},
    onVoiceInput: () -> Unit = {},
    onCancelVoiceInput: () -> Unit = {},
    onConfirmTranscript: () -> Unit = {},
    onSubmitAssistantQuery: () -> Unit = {},
    onCancelAssistantQuery: () -> Unit = {},
    onRetryAssistantQuery: () -> Unit = {},
    onItineraryCitySelected: (ItineraryCity) -> Unit = {},
    onItineraryDateChanged: (String) -> Unit = {},
    onItineraryStartTimeChanged: (String) -> Unit = {},
    onItineraryEndTimeChanged: (String) -> Unit = {},
    onItineraryMaximumStopsChanged: (String) -> Unit = {},
    onItineraryNotesChanged: (String) -> Unit = {},
    onGenerateItinerary: () -> Unit = {},
    onCancelItineraryGeneration: () -> Unit = {},
    onRetryItineraryGeneration: () -> Unit = {},
    onSaveItinerary: () -> Unit = {},
    onOpenSavedItinerary: (String) -> Unit = {},
    onDeleteSavedItinerary: () -> Unit = {},
    onReturnToItineraryGeneration: () -> Unit = {},
    onOpenMicrophoneSettings: () -> Unit = {},
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
    onBeginPreferenceEdit: () -> Unit = {},
    onCancelPreferenceEdit: () -> Unit = {},
    onToggleInterest: (TravelInterest) -> Unit = {},
    onSelectPace: (TravelPace?) -> Unit = {},
    onSelectBudget: (BudgetPreference?) -> Unit = {},
    onSavePreferences: () -> Unit = {},
    onRequestPreferenceReset: () -> Unit = {},
    onDismissPreferenceReset: () -> Unit = {},
    onConfirmPreferenceReset: () -> Unit = {},
    onRetryPreferenceSync: () -> Unit = {},
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
                onDemoLocationPresetSelected = onDemoLocationPresetSelected,
                onPoiSelected = { poiId ->
                    navController.navigate(PoiDetailDestination.createRoute(poiId)) {
                        launchSingleTop = true
                    }
                },
            )
        }
        composable(TopLevelDestination.ASSISTANT.route) {
            AssistantScreen(
                uiState = assistantUiState,
                isOffline = connectivityUiState == ConnectivityUiState.Offline,
                onQueryChanged = onAssistantQueryChanged,
                onVoiceInput = onVoiceInput,
                onCancelVoiceInput = onCancelVoiceInput,
                onConfirmTranscript = onConfirmTranscript,
                onSubmitQuery = onSubmitAssistantQuery,
                onCancelQuery = onCancelAssistantQuery,
                onRetryQuery = onRetryAssistantQuery,
                onOpenPermissionSettings = onOpenMicrophoneSettings,
            )
        }
        composable(TopLevelDestination.ITINERARY.route) {
            ItineraryScreen(
                uiState = itineraryUiState,
                onCitySelected = onItineraryCitySelected,
                onLocalDateChanged = onItineraryDateChanged,
                onStartTimeChanged = onItineraryStartTimeChanged,
                onEndTimeChanged = onItineraryEndTimeChanged,
                onMaximumStopsChanged = onItineraryMaximumStopsChanged,
                onNotesChanged = onItineraryNotesChanged,
                onGenerate = onGenerateItinerary,
                onCancelGeneration = onCancelItineraryGeneration,
                onRetry = onRetryItineraryGeneration,
                onSave = onSaveItinerary,
                onOpenSaved = onOpenSavedItinerary,
                onDeleteSaved = onDeleteSavedItinerary,
                onReturnToGeneration = onReturnToItineraryGeneration,
            )
        }
        composable(TopLevelDestination.DOWNLOADS.route) {
            DownloadsScreen(
                uiState = downloadsUiState ?: localPackageUiState.toDownloadsUiState(),
                connectivity = connectivityUiState,
                onDownload = onDownloadPackage,
                onRetry = onRetryPackageDownload,
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
                onGoogleSignIn = onGoogleSignIn,
                onRefreshVerification = onAuthRefreshVerification,
                onResendVerificationEmail = onAuthResendVerificationEmail,
                onSignOut = onAuthSignOut,
                onRetrySession = onAuthRetrySession,
                preferenceUiState = preferenceProfileUiState,
                onBeginPreferenceEdit = onBeginPreferenceEdit,
                onCancelPreferenceEdit = onCancelPreferenceEdit,
                onToggleInterest = onToggleInterest,
                onSelectPace = onSelectPace,
                onSelectBudget = onSelectBudget,
                onSavePreferences = onSavePreferences,
                onRequestPreferenceReset = onRequestPreferenceReset,
                onDismissPreferenceReset = onDismissPreferenceReset,
                onConfirmPreferenceReset = onConfirmPreferenceReset,
                onRetryPreferenceSync = onRetryPreferenceSync,
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

private fun LocalPackageUiState.toDownloadsUiState(): DownloadsUiState = when (this) {
    LocalPackageUiState.Loading -> DownloadsUiState()
    LocalPackageUiState.Unavailable,
    LocalPackageUiState.Error -> DownloadsUiState(
        isLoading = false,
        status = DownloadsStatus.Idle,
    )
    is LocalPackageUiState.Available -> DownloadsUiState(
        isLoading = false,
        activePackage = ActivePackageMetadata(
            packageId = "local-package",
            city = PackageCity.HCMC,
            contentVersion = version,
            publishedAtEpochMillis = publishedAtEpochMillis,
            origin = PackageOrigin.DOWNLOADED,
        ),
        status = DownloadsStatus.Idle,
    )
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
