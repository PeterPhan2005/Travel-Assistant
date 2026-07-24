package com.kltn.travelassistant

import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.assertIsEnabled
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.kltn.travelassistant.feature.auth.domain.AuthSession
import com.kltn.travelassistant.feature.auth.domain.AuthUser
import com.kltn.travelassistant.feature.auth.presentation.ProfileUiState
import com.kltn.travelassistant.feature.home.presentation.HomeUiState
import com.kltn.travelassistant.navigation.TopLevelDestination
import com.kltn.travelassistant.navigation.navigationItemTestTag
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class ProfileAuthNavigationTest {
    @get:Rule
    val composeRule = createComposeRule()

    @Test
    fun profileSessionPersistsAcrossNavigationAndSignedOutExploreRemainsUsable() {
        var profileState by mutableStateOf(
            ProfileUiState(session = AuthSession.SignedOut),
        )
        composeRule.setContent {
            TravelAssistantAppContent(
                homeUiState = HomeUiState(appName = "Travel Assistant"),
                profileUiState = profileState,
                onUseCurrentLocation = {},
                onOpenLocationSettings = {},
                onNearbyQueryChanged = {},
            )
        }

        composeRule.onNodeWithText(getString(R.string.location_use_current))
            .assertIsDisplayed()
            .assertIsEnabled()
        composeRule.onNodeWithTag(navigationItemTestTag(TopLevelDestination.PROFILE))
            .performClick()
        composeRule.onNodeWithText(getString(R.string.auth_signed_out_explanation))
            .assertIsDisplayed()

        composeRule.runOnIdle {
            profileState = ProfileUiState(
                session = AuthSession.Authenticated(verifiedUser),
            )
        }
        composeRule.onNodeWithText(getString(R.string.auth_authenticated_title))
            .assertIsDisplayed()
        composeRule.onNodeWithTag(navigationItemTestTag(TopLevelDestination.EXPLORE))
            .performClick()
        composeRule.onNodeWithText(getString(R.string.location_use_current))
            .assertIsDisplayed()
            .assertIsEnabled()
        composeRule.onNodeWithTag(navigationItemTestTag(TopLevelDestination.PROFILE))
            .performClick()
        composeRule.onNodeWithText(getString(R.string.auth_account_email, verifiedUser.email))
            .assertIsDisplayed()
    }

    private fun getString(resourceId: Int, vararg formatArgs: Any): String =
        ApplicationProvider.getApplicationContext<android.content.Context>()
            .getString(resourceId, *formatArgs)

    private companion object {
        val verifiedUser = AuthUser(
            uid = "uid-private",
            email = "traveler@example.com",
            isEmailVerified = true,
        )
    }
}
