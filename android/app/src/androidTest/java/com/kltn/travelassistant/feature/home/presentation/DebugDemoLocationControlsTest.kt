package com.kltn.travelassistant.feature.home.presentation

import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performScrollTo
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.kltn.travelassistant.MainActivity
import com.kltn.travelassistant.R
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class DebugDemoLocationControlsTest {
    @get:Rule
    val composeRule = createAndroidComposeRule<MainActivity>()

    @Test
    fun debugControlsSelectBothPresetsAndKeepNormalCurrentLocationAction() {
        composeRule.onNodeWithText(getString(R.string.location_use_current))
            .performScrollTo()
            .assertIsDisplayed()
        composeRule.onNodeWithText(HCMC_LABEL)
            .performScrollTo()
            .assertIsDisplayed()
            .performClick()
        composeRule.onNodeWithText(getString(R.string.location_demo_active, HCMC_LABEL))
            .performScrollTo()
            .assertIsDisplayed()

        composeRule.onNodeWithText(BANGKOK_LABEL)
            .performScrollTo()
            .assertIsDisplayed()
            .performClick()
        composeRule.onNodeWithText(getString(R.string.location_demo_active, BANGKOK_LABEL))
            .performScrollTo()
            .assertIsDisplayed()
        composeRule.onNodeWithText(getString(R.string.location_refresh))
            .performScrollTo()
            .assertIsDisplayed()
    }

    private fun getString(resourceId: Int, vararg formatArgs: Any): String =
        ApplicationProvider.getApplicationContext<android.content.Context>()
            .getString(resourceId, *formatArgs)

    private companion object {
        const val HCMC_LABEL = "Demo: TP.HCM"
        const val BANGKOK_LABEL = "Demo: Bangkok"
    }
}
