package com.kltn.travelassistant.feature.itinerary.presentation

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
class ItineraryNavigationLifecycleTest {
    @get:Rule
    val composeRule = createComposeRule()

    @Test
    fun leavingItineraryInvokesCancellationOnceAndReturningDoesNotGenerateOrSave() {
        var screenLeftCount = 0
        var generateCount = 0
        var saveCount = 0
        composeRule.setContent {
            TravelAssistantAppContent(
                homeUiState = HomeUiState(appName = "Travel Assistant"),
                onUseCurrentLocation = {},
                onOpenLocationSettings = {},
                onNearbyQueryChanged = {},
                onGenerateItinerary = { generateCount += 1 },
                onSaveItinerary = { saveCount += 1 },
                onItineraryScreenLeft = { screenLeftCount += 1 },
            )
        }

        composeRule.onNodeWithTag(
            navigationItemTestTag(TopLevelDestination.ITINERARY),
        ).performClick().assertIsSelected()
        composeRule.onNodeWithTag(
            navigationItemTestTag(TopLevelDestination.EXPLORE),
        ).performClick().assertIsSelected()

        assertEquals(1, screenLeftCount)
        assertEquals(0, generateCount)
        assertEquals(0, saveCount)

        composeRule.onNodeWithTag(
            navigationItemTestTag(TopLevelDestination.ITINERARY),
        ).performClick().assertIsSelected()

        assertEquals(1, screenLeftCount)
        assertEquals(0, generateCount)
        assertEquals(0, saveCount)
    }
}
