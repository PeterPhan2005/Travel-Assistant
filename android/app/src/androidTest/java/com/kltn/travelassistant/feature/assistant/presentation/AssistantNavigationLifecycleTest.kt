package com.kltn.travelassistant.feature.assistant.presentation

import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.compose.ui.test.assertIsSelected
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.performClick
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.kltn.travelassistant.TravelAssistantAppContent
import com.kltn.travelassistant.feature.home.presentation.HomeUiState
import com.kltn.travelassistant.navigation.TopLevelDestination
import com.kltn.travelassistant.navigation.navigationItemTestTag
import org.junit.Assert.assertEquals
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class AssistantNavigationLifecycleTest {
    @get:Rule
    val composeRule = createComposeRule()

    @Test
    fun disposingAssistantDestinationInvokesScreenLeftExactlyOnce() {
        var showApp by mutableStateOf(true)
        var screenLeftCount = 0
        composeRule.setContent {
            if (showApp) {
                TestAppContent(
                    onAssistantScreenLeft = { screenLeftCount += 1 },
                )
            }
        }
        composeRule.onNodeWithTag(
            navigationItemTestTag(TopLevelDestination.ASSISTANT),
        ).performClick().assertIsSelected()

        composeRule.runOnUiThread {
            showApp = false
        }
        composeRule.waitForIdle()

        assertEquals(1, screenLeftCount)
    }

    @Test
    fun movingToAnotherTopLevelDestinationCancelsAndReturningDoesNotStartVoice() {
        var screenLeftCount = 0
        var voiceStartCount = 0
        composeRule.setContent {
            TestAppContent(
                onVoiceInput = { voiceStartCount += 1 },
                onAssistantScreenLeft = { screenLeftCount += 1 },
            )
        }
        composeRule.onNodeWithTag(
            navigationItemTestTag(TopLevelDestination.ASSISTANT),
        ).performClick().assertIsSelected()

        composeRule.onNodeWithTag(
            navigationItemTestTag(TopLevelDestination.ITINERARY),
        ).performClick().assertIsSelected()

        assertEquals(1, screenLeftCount)

        composeRule.onNodeWithTag(
            navigationItemTestTag(TopLevelDestination.ASSISTANT),
        ).performClick()
        composeRule.onNodeWithTag(
            navigationItemTestTag(TopLevelDestination.ASSISTANT),
        ).assertIsSelected()

        assertEquals(0, voiceStartCount)
        assertEquals(1, screenLeftCount)
    }

    @androidx.compose.runtime.Composable
    private fun TestAppContent(
        onVoiceInput: () -> Unit = {},
        onAssistantScreenLeft: () -> Unit,
    ) {
        TravelAssistantAppContent(
            homeUiState = HomeUiState(appName = "Travel Assistant"),
            onUseCurrentLocation = {},
            onOpenLocationSettings = {},
            onNearbyQueryChanged = {},
            onVoiceInput = onVoiceInput,
            onAssistantScreenLeft = onAssistantScreenLeft,
        )
    }
}
