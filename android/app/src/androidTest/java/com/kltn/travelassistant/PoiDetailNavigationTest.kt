package com.kltn.travelassistant

import androidx.compose.ui.test.assertCountEquals
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onAllNodesWithTag
import androidx.compose.ui.test.onNodeWithContentDescription
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performScrollTo
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.kltn.travelassistant.data.location.DeviceLocation
import com.kltn.travelassistant.feature.home.presentation.HomeUiState
import com.kltn.travelassistant.feature.home.presentation.LocationUiState
import com.kltn.travelassistant.feature.home.presentation.NearbySearchUiState
import com.kltn.travelassistant.feature.nearby.domain.NearbyPoi
import com.kltn.travelassistant.feature.nearby.domain.PoiCategoryLabel
import com.kltn.travelassistant.feature.poi.domain.PoiDetail
import com.kltn.travelassistant.feature.poi.presentation.PoiDetailScreen
import com.kltn.travelassistant.feature.poi.presentation.PoiDetailUiState
import com.kltn.travelassistant.navigation.TopLevelDestination
import com.kltn.travelassistant.navigation.navigationItemTestTag
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class PoiDetailNavigationTest {
    @get:Rule
    val composeRule = createComposeRule()

    @Test
    fun selectingResultsOpensLocalDetailHidesBottomBarAndBackPreservesExploreQuery() {
        composeRule.setContent {
            TravelAssistantAppContent(
                homeUiState = exploreState,
                onUseCurrentLocation = {},
                onOpenLocationSettings = {},
                onNearbyQueryChanged = {},
                poiDetailContent = { poiId, onBack ->
                    PoiDetailScreen(
                        uiState = PoiDetailUiState.Content(details.getValue(poiId)),
                        onBack = onBack,
                        onRetry = {},
                    )
                },
            )
        }

        openDetailAndReturn("Chợ Bến Thành")
        composeRule.onNodeWithText(exploreState.nearbyQuery).assertIsDisplayed()
        openDetailAndReturn("Bưu điện Trung tâm Sài Gòn")
    }

    private fun openDetailAndReturn(name: String) {
        composeRule.onNodeWithText(name).performScrollTo().performClick()

        composeRule.onNodeWithText(name).assertIsDisplayed()
        TopLevelDestination.all.forEach { destination ->
            composeRule.onAllNodesWithTag(navigationItemTestTag(destination)).assertCountEquals(0)
        }

        composeRule.onNodeWithContentDescription(getString(R.string.poi_detail_back)).performClick()

        composeRule.onNodeWithText(name).assertIsDisplayed()
        composeRule.onAllNodesWithTag(
            navigationItemTestTag(TopLevelDestination.EXPLORE),
        ).assertCountEquals(1)
    }

    private fun getString(resourceId: Int): String =
        ApplicationProvider.getApplicationContext<android.content.Context>().getString(resourceId)

    private companion object {
        val results = listOf(
            NearbyPoi(
                poiId = "ben-thanh",
                displayName = "Chợ Bến Thành",
                category = "market",
                categoryLabel = PoiCategoryLabel.MARKET,
                distanceMeters = 250.0,
            ),
            NearbyPoi(
                poiId = "post-office",
                displayName = "Bưu điện Trung tâm Sài Gòn",
                category = "landmark",
                categoryLabel = PoiCategoryLabel.LANDMARK,
                distanceMeters = 500.0,
            ),
        )
        val exploreState = HomeUiState(
            appName = "Travel Assistant",
            locationState = LocationUiState.Available(
                DeviceLocation(
                    latitude = 10.7799,
                    longitude = 106.7,
                    accuracyMeters = 10f,
                    capturedAtEpochMillis = 1,
                ),
            ),
            nearbyQuery = "địa điểm",
            nearbySearchState = NearbySearchUiState.Content(results),
        )
        val details = results.associate { poi ->
            poi.poiId to PoiDetail(
                poiId = poi.poiId,
                name = poi.displayName,
                category = poi.categoryLabel,
                city = "Ho Chi Minh City",
                area = null,
                address = null,
                shortDescription = null,
                menuItems = emptyList(),
                narration = null,
            )
        }
    }
}
