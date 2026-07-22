package com.kltn.travelassistant.feature.home.presentation

import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.kltn.travelassistant.R
import com.kltn.travelassistant.data.location.DeviceLocation
import com.kltn.travelassistant.ui.theme.TravelAssistantTheme
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
    }

    private fun setHomeContent(
        state: LocationUiState,
        onUseCurrentLocation: () -> Unit = {},
    ) {
        composeRule.setContent {
            TravelAssistantTheme(dynamicColor = false) {
                HomeScreen(
                    uiState = HomeUiState(
                        appName = "Travel Assistant",
                        locationState = state,
                    ),
                    onUseCurrentLocation = onUseCurrentLocation,
                    onOpenLocationSettings = {},
                )
            }
        }
    }

    private fun getString(resourceId: Int, vararg formatArgs: Any): String =
        ApplicationProvider.getApplicationContext<android.content.Context>()
            .getString(resourceId, *formatArgs)
}
