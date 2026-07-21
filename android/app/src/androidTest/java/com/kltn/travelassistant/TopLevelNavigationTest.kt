package com.kltn.travelassistant

import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.assertIsSelected
import androidx.compose.ui.test.hasText
import androidx.compose.ui.test.isHeading
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.performClick
import androidx.test.espresso.Espresso.pressBack
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.kltn.travelassistant.navigation.TopLevelDestination
import com.kltn.travelassistant.navigation.navigationItemTestTag
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class TopLevelNavigationTest {
    @get:Rule
    val composeRule = createAndroidComposeRule<MainActivity>()

    @Test
    fun everyNavigationItemIsVisible() {
        TopLevelDestination.all.forEach { destination ->
            composeRule
                .onNodeWithTag(navigationItemTestTag(destination))
                .assertIsDisplayed()
        }
    }

    @Test
    fun tappingEachItemShowsAndSelectsItsDestination() {
        TopLevelDestination.all.forEach { destination ->
            val label = composeRule.activity.getString(destination.labelRes)

            composeRule
                .onNodeWithTag(navigationItemTestTag(destination))
                .performClick()

            composeRule
                .onNodeWithTag(navigationItemTestTag(destination))
                .assertIsSelected()
            composeRule
                .onNode(hasText(label) and isHeading())
                .assertIsDisplayed()
        }
    }

    @Test
    fun backFromNonStartDestinationReturnsToExplore() {
        repeat(2) {
            composeRule
                .onNodeWithTag(navigationItemTestTag(TopLevelDestination.PROFILE))
                .performClick()
        }

        pressBack()

        composeRule
            .onNodeWithTag(navigationItemTestTag(TopLevelDestination.EXPLORE))
            .assertIsSelected()
        composeRule
            .onNode(
                hasText(composeRule.activity.getString(R.string.destination_explore)) and isHeading(),
            )
            .assertIsDisplayed()
    }
}
