package com.kltn.travelassistant.feature.poi.presentation

import androidx.compose.ui.test.assertCountEquals
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.onAllNodesWithText
import androidx.compose.ui.test.performClick
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.kltn.travelassistant.R
import com.kltn.travelassistant.feature.nearby.domain.PoiCategoryLabel
import com.kltn.travelassistant.feature.poi.domain.PoiDetail
import com.kltn.travelassistant.feature.poi.domain.PoiMenuItem
import com.kltn.travelassistant.feature.poi.domain.PoiNarration
import com.kltn.travelassistant.feature.poi.domain.PoiNavigationTarget
import com.kltn.travelassistant.ui.theme.TravelAssistantTheme
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotEquals
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class PoiDetailScreenTest {
    @get:Rule
    val composeRule = createComposeRule()

    @Test
    fun loadingNotFoundAndErrorStatesUseLocalizedCopy() {
        setScreen(PoiDetailUiState.Loading)
        composeRule.onNodeWithText(getString(R.string.poi_detail_loading)).assertIsDisplayed()
    }

    @Test
    fun notFoundStateUsesLocalizedCopy() {
        setScreen(PoiDetailUiState.NotFound)
        composeRule.onNodeWithText(getString(R.string.poi_detail_not_found)).assertIsDisplayed()
    }

    @Test
    fun errorStateShowsRetryAndInvokesIt() {
        var retried = false
        setScreen(PoiDetailUiState.Error, onRetry = { retried = true })

        composeRule.onNodeWithText(getString(R.string.poi_detail_error)).assertIsDisplayed()
        composeRule.onNodeWithText(getString(R.string.poi_detail_retry)).performClick()

        assertTrue(retried)
    }

    @Test
    fun absentOptionalFieldsMenuAndNarrationAreOmitted() {
        setScreen(PoiDetailUiState.Content(minimalDetail))

        composeRule.onNodeWithText(minimalDetail.name).assertIsDisplayed()
        composeRule.onNodeWithText(getString(R.string.nearby_category_market)).assertIsDisplayed()
        composeRule.onNodeWithText(getString(R.string.poi_detail_city, minimalDetail.city))
            .assertIsDisplayed()
        composeRule.onAllNodesWithText(getString(R.string.poi_detail_menu_title)).assertCountEquals(0)
        composeRule.onAllNodesWithText(getString(R.string.poi_detail_narration_title)).assertCountEquals(0)
        composeRule.onAllNodesWithText("N/A").assertCountEquals(0)
        composeRule.onAllNodesWithText("Unknown").assertCountEquals(0)
    }

    @Test
    fun navigationActionPassesStoredPoiTargetWithoutDisplayingCoordinates() {
        var openedTarget: PoiNavigationTarget? = null
        setScreen(
            PoiDetailUiState.Content(minimalDetail),
            onNavigate = { openedTarget = it },
        )

        composeRule.onNodeWithText(getString(R.string.poi_detail_navigate))
            .assertIsDisplayed()
            .performClick()

        assertEquals(minimalDetail.navigationTarget, openedTarget)
        composeRule.onAllNodesWithText(minimalDetail.navigationTarget!!.latitude.toString())
            .assertCountEquals(0)
        composeRule.onAllNodesWithText(minimalDetail.navigationTarget.longitude.toString())
            .assertCountEquals(0)
    }

    @Test
    fun navigationActionIsOmittedWithoutTarget() {
        setScreen(PoiDetailUiState.Content(minimalDetail.copy(navigationTarget = null)))

        composeRule.onAllNodesWithText(getString(R.string.poi_detail_navigate)).assertCountEquals(0)
    }

    @Test
    fun localizedNavigationErrorsRemainRecoverable() {
        var attempts = 0
        setScreen(
            PoiDetailUiState.Content(minimalDetail),
            navigationError = PoiNavigationError.NO_COMPATIBLE_APPLICATION,
            onNavigate = { attempts += 1 },
        )

        composeRule.onNodeWithText(
            getString(R.string.poi_detail_navigation_unavailable),
        ).assertIsDisplayed()
        composeRule.onNodeWithText(getString(R.string.poi_detail_navigate)).performClick()

        assertEquals(1, attempts)
    }

    @Test
    fun invalidDestinationAndLaunchFailureUseDifferentLocalizedMessages() {
        val unavailable = getString(R.string.poi_detail_navigation_unavailable)
        val invalid = getString(R.string.poi_detail_navigation_invalid_destination)
        val failed = getString(R.string.poi_detail_navigation_launch_failed)

        assertNotEquals(unavailable, invalid)
        assertNotEquals(unavailable, failed)
        assertNotEquals(invalid, failed)
    }

    @Test
    fun menuFreshnessAndNarrationSourceAreVisibleWithStoredData() {
        val menuItem = PoiMenuItem(
            dishName = "Cà phê sữa",
            priceMinorUnits = 45_000,
            currencyCode = "VND",
            sourceType = "menu_curated",
            updatedAtEpochMillis = 1_721_510_400_000,
        )
        val detail = minimalDetail.copy(
            area = "Quận 1",
            address = "1 Đường thử nghiệm",
            shortDescription = "Mô tả đã lưu.",
            menuItems = listOf(menuItem),
            narration = PoiNarration(
                content = "Nội dung thuyết minh có nguồn.",
                sourceLabel = "Ban quản lý điểm đến",
            ),
        )
        setScreen(PoiDetailUiState.Content(detail))

        composeRule.onNodeWithText(menuItem.dishName).assertIsDisplayed()
        composeRule.onNodeWithText(
            getString(
                R.string.poi_detail_price_updated,
                PriceUpdateDateFormatter.format(menuItem.updatedAtEpochMillis)!!,
            ),
        ).assertIsDisplayed()
        composeRule.onNodeWithText(
            getString(R.string.poi_detail_price_source, menuItem.sourceType),
        ).assertIsDisplayed()
        composeRule.onNodeWithText(detail.narration!!.content).assertIsDisplayed()
        composeRule.onNodeWithText(
            getString(R.string.poi_detail_narration_source, detail.narration.sourceLabel),
        ).assertIsDisplayed()
    }

    @Test
    fun zeroPlaceholderPriceDoesNotCreateMenuSection() {
        setScreen(
            PoiDetailUiState.Content(
                minimalDetail.copy(
                    menuItems = listOf(
                        PoiMenuItem(
                            dishName = "Giá chưa xác nhận",
                            priceMinorUnits = 0,
                            currencyCode = "VND",
                            sourceType = "curated_menu",
                            updatedAtEpochMillis = 1_721_510_400_000,
                        ),
                    ),
                ),
            ),
        )

        composeRule.onAllNodesWithText(getString(R.string.poi_detail_menu_title)).assertCountEquals(0)
        composeRule.onAllNodesWithText("Giá chưa xác nhận").assertCountEquals(0)
    }

    private fun setScreen(
        state: PoiDetailUiState,
        onRetry: () -> Unit = {},
        navigationError: PoiNavigationError? = null,
        onNavigate: (PoiNavigationTarget) -> Unit = {},
    ) {
        composeRule.setContent {
            TravelAssistantTheme(dynamicColor = false) {
                PoiDetailScreen(
                    uiState = state,
                    onBack = {},
                    onRetry = onRetry,
                    navigationError = navigationError,
                    onNavigate = onNavigate,
                )
            }
        }
    }

    private fun getString(resourceId: Int, vararg formatArgs: Any): String =
        ApplicationProvider.getApplicationContext<android.content.Context>()
            .getString(resourceId, *formatArgs)

    private companion object {
        val minimalDetail = PoiDetail(
            poiId = "ben-thanh",
            name = "Chợ Bến Thành",
            category = PoiCategoryLabel.MARKET,
            city = "Ho Chi Minh City",
            area = null,
            address = null,
            shortDescription = null,
            menuItems = emptyList(),
            narration = null,
            navigationTarget = PoiNavigationTarget(
                poiId = "ben-thanh",
                displayName = "Chợ Bến Thành",
                latitude = 10.7725,
                longitude = 106.6980,
            ),
        )
    }
}
