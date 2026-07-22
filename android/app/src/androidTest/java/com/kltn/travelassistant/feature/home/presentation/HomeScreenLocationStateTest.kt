package com.kltn.travelassistant.feature.home.presentation

import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performTextInput
import androidx.compose.ui.test.performClick
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.kltn.travelassistant.R
import com.kltn.travelassistant.data.location.DeviceLocation
import com.kltn.travelassistant.feature.nearby.domain.NearbyPoi
import com.kltn.travelassistant.feature.nearby.domain.PoiCategoryLabel
import com.kltn.travelassistant.feature.nearby.presentation.DistanceFormatter
import com.kltn.travelassistant.ui.theme.TravelAssistantTheme
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class HomeScreenLocationStateTest {
    @get:Rule
    val composeRule = createComposeRule()

    @Test
    fun idleActionIsVisibleAndInvokesUserAction() {
        var actionInvoked = false
        setHomeContent(
            state = LocationUiState.Idle,
            onUseCurrentLocation = { actionInvoked = true },
        )

        composeRule.onNodeWithText(getString(R.string.location_use_current))
            .assertIsDisplayed()
            .performClick()

        assertTrue(actionInvoked)
    }

    @Test
    fun loadingStateIsVisible() {
        setHomeContent(state = LocationUiState.Loading)

        composeRule.onNodeWithText(getString(R.string.location_loading)).assertIsDisplayed()
    }

    @Test
    fun deniedStateShowsRetryAndSettingsRecovery() {
        setHomeContent(
            state = LocationUiState.PermissionDenied(canRequestPermissionAgain = false),
        )

        composeRule.onNodeWithText(getString(R.string.location_permission_denied))
            .assertIsDisplayed()
        composeRule.onNodeWithText(getString(R.string.location_retry)).assertIsDisplayed()
        composeRule.onNodeWithText(getString(R.string.location_open_settings)).assertIsDisplayed()
    }

    @Test
    fun errorStateShowsMessageAndRetry() {
        setHomeContent(
            state = LocationUiState.Error(LocationError.PROVIDER_UNAVAILABLE),
        )

        composeRule.onNodeWithText(getString(R.string.location_provider_unavailable))
            .assertIsDisplayed()
        composeRule.onNodeWithText(getString(R.string.location_retry)).assertIsDisplayed()
    }

    @Test
    fun availableStateShowsLocalOnlyConfirmationWithoutCoordinates() {
        setHomeContent(
            state = LocationUiState.Available(
                DeviceLocation(
                    latitude = 10.7799,
                    longitude = 106.7,
                    accuracyMeters = 15f,
                    capturedAtEpochMillis = 1_753_200_000_000L,
                ),
            ),
        )

        composeRule.onNodeWithText(getString(R.string.location_available_local_only))
            .assertIsDisplayed()
        composeRule.onNodeWithText(getString(R.string.location_accuracy, 15))
            .assertIsDisplayed()
        composeRule.onNodeWithText(getString(R.string.location_refresh)).assertIsDisplayed()
        composeRule.onNodeWithText(getString(R.string.nearby_search_label)).assertIsDisplayed()
    }

    @Test
    fun nearbyContentShowsSearchFieldResultNameCategoryAndKilometres() {
        val poi = NearbyPoi(
            poiId = "ben-thanh",
            displayName = "Chợ Bến Thành",
            category = "market",
            categoryLabel = PoiCategoryLabel.MARKET,
            distanceMeters = 250.0,
        )
        setHomeContent(
            state = availableLocationState(),
            nearbySearchState = NearbySearchUiState.Content(listOf(poi)),
        )

        composeRule.onNodeWithText(getString(R.string.nearby_search_label)).assertIsDisplayed()
        composeRule.onNodeWithText(poi.displayName).assertIsDisplayed()
        composeRule.onNodeWithText(getString(R.string.nearby_category_market)).assertIsDisplayed()
        composeRule.onNodeWithText(
            getString(
                R.string.nearby_distance_km,
                DistanceFormatter.formatKilometresValue(250.0),
            ),
        ).assertIsDisplayed()
        composeRule.onNodeWithText(getString(R.string.nearby_straight_line_notice))
            .assertIsDisplayed()
    }

    @Test
    fun nearbyEmptyStateIsVisible() {
        setHomeContent(
            state = availableLocationState(),
            nearbySearchState = NearbySearchUiState.Empty,
        )

        composeRule.onNodeWithText(getString(R.string.nearby_empty)).assertIsDisplayed()
    }

    @Test
    fun searchFieldForwardsQueryChanges() {
        var query = ""
        setHomeContent(
            state = availableLocationState(),
            onNearbyQueryChanged = { query = it },
        )

        composeRule.onNodeWithText(getString(R.string.nearby_search_label))
            .performTextInput("ben thanh")

        assertEquals("ben thanh", query)
    }

    private fun setHomeContent(
        state: LocationUiState,
        onUseCurrentLocation: () -> Unit = {},
        nearbySearchState: NearbySearchUiState = NearbySearchUiState.WaitingForLocation,
        onNearbyQueryChanged: (String) -> Unit = {},
    ) {
        composeRule.setContent {
            TravelAssistantTheme(dynamicColor = false) {
                HomeScreen(
                    uiState = HomeUiState(
                        appName = "Travel Assistant",
                        locationState = state,
                        nearbySearchState = nearbySearchState,
                    ),
                    onUseCurrentLocation = onUseCurrentLocation,
                    onOpenLocationSettings = {},
                    onNearbyQueryChanged = onNearbyQueryChanged,
                )
            }
        }
    }

    private fun availableLocationState() = LocationUiState.Available(
        DeviceLocation(
            latitude = 10.7799,
            longitude = 106.7,
            accuracyMeters = 15f,
            capturedAtEpochMillis = 1_753_200_000_000L,
        ),
    )

    private fun getString(resourceId: Int, vararg formatArgs: Any): String =
        ApplicationProvider.getApplicationContext<android.content.Context>()
            .getString(resourceId, *formatArgs)
}
