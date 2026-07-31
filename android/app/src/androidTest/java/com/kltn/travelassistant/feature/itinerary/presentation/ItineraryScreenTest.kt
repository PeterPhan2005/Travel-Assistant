package com.kltn.travelassistant.feature.itinerary.presentation

import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.compose.ui.test.assert
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.assertIsEnabled
import androidx.compose.ui.test.assertIsNotEnabled
import androidx.compose.ui.test.hasContentDescription
import androidx.compose.ui.test.hasSetTextAction
import androidx.compose.ui.test.hasText
import androidx.compose.ui.test.isHeading
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performScrollTo
import androidx.compose.ui.test.performTextInput
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.kltn.travelassistant.R
import com.kltn.travelassistant.feature.itinerary.domain.ItineraryCity
import com.kltn.travelassistant.feature.itinerary.domain.ItineraryDraft
import com.kltn.travelassistant.feature.itinerary.domain.ItineraryDraftFailure
import com.kltn.travelassistant.feature.itinerary.domain.ItineraryDraftItem
import com.kltn.travelassistant.feature.itinerary.domain.ItineraryDraftWarning
import com.kltn.travelassistant.ui.theme.TravelAssistantTheme
import java.time.LocalDate
import java.time.LocalTime
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class ItineraryScreenTest {
    @get:Rule
    val composeRule = createComposeRule()

    @Test
    fun formReplacesPlaceholderAndExposesVietnameseControlsAndHeading() {
        setItineraryContent(ItineraryUiState())

        composeRule.onNode(
            hasText(getString(R.string.destination_itinerary)) and isHeading(),
        ).assertIsDisplayed()
        composeRule.onNodeWithText(getString(R.string.feature_coming_later))
            .assertDoesNotExist()
        listOf(
            R.string.itinerary_city_label,
            R.string.itinerary_city_hcmc,
            R.string.itinerary_city_bangkok,
            R.string.itinerary_date_label,
            R.string.itinerary_start_time_label,
            R.string.itinerary_end_time_label,
            R.string.itinerary_maximum_stops_label,
            R.string.itinerary_notes_label,
            R.string.itinerary_generate,
            R.string.itinerary_save,
        ).forEach { resource ->
            composeRule.onNodeWithText(getString(resource)).assertExists()
        }
        composeRule.onNodeWithTag(ITINERARY_SAVE_TEST_TAG).assertIsNotEnabled()
        composeRule.onNode(hasContentDescription("Chọn thành phố cho lịch trình"))
            .assertExists()
    }

    @Test
    fun dateAndTimeSeparatorsAreForwardedUnchangedWithoutAutomaticGeneration() {
        var uiState by mutableStateOf(ItineraryUiState())
        var generateCount = 0
        composeRule.setContent {
            TravelAssistantTheme(dynamicColor = false) {
                ItineraryScreen(
                    uiState = uiState,
                    onCitySelected = {
                        uiState = uiState.copy(form = uiState.form.copy(city = it))
                    },
                    onLocalDateChanged = {
                        uiState = uiState.copy(form = uiState.form.copy(localDate = it))
                    },
                    onStartTimeChanged = {
                        uiState = uiState.copy(form = uiState.form.copy(startLocalTime = it))
                    },
                    onEndTimeChanged = {
                        uiState = uiState.copy(form = uiState.form.copy(endLocalTime = it))
                    },
                    onMaximumStopsChanged = {},
                    onNotesChanged = {},
                    onGenerate = { generateCount += 1 },
                    onCancelGeneration = {},
                    onRetry = {},
                    onSave = {},
                )
            }
        }

        assertEquals(0, generateCount)
        composeRule.onNodeWithText(getString(R.string.itinerary_city_bangkok))
            .performClick()
        composeRule.onNode(
            hasText(getString(R.string.itinerary_date_label)) and hasSetTextAction(),
        ).performTextInput("2026-08-01")
        composeRule.onNode(
            hasText(getString(R.string.itinerary_start_time_label)) and hasSetTextAction(),
        ).performTextInput("09:15")
        composeRule.onNode(
            hasText(getString(R.string.itinerary_end_time_label)) and hasSetTextAction(),
        ).performTextInput("17:45")
        assertEquals(ItineraryCity.BANGKOK, uiState.form.city)
        assertEquals("2026-08-01", uiState.form.localDate)
        assertEquals("09:15", uiState.form.startLocalTime)
        assertEquals("17:45", uiState.form.endLocalTime)
        assertEquals(0, generateCount)

        composeRule.onNodeWithTag(ITINERARY_GENERATE_TEST_TAG)
            .performScrollTo()
            .assertIsEnabled()
            .performClick()
        assertEquals(1, generateCount)
    }

    @Test
    fun invalidMessagesRenderNextToAssociatedControls() {
        setItineraryContent(
            ItineraryUiState(
                fieldErrors = ItineraryFieldErrors(
                    city = ItineraryValidationError.CITY_REQUIRED,
                    localDate = ItineraryValidationError.DATE_INVALID,
                    endLocalTime = ItineraryValidationError.END_NOT_AFTER_START,
                    maximumStops = ItineraryValidationError.MAXIMUM_STOPS_OUT_OF_RANGE,
                    notes = ItineraryValidationError.NOTES_TOO_LONG,
                ),
            ),
        )

        listOf(
            R.string.itinerary_error_city_required,
            R.string.itinerary_error_date_invalid,
            R.string.itinerary_error_end_not_after_start,
            R.string.itinerary_error_maximum_stops_out_of_range,
            R.string.itinerary_error_notes_too_long,
        ).forEach { resource ->
            composeRule.onNodeWithText(getString(resource)).assertExists()
        }
    }

    @Test
    fun loadingCancelRetryAndUnavailableStatesAreExplicit() {
        var cancelled = false
        var retried = false
        var uiState by mutableStateOf(
            ItineraryUiState(generationState = ItineraryGenerationUiState.Loading),
        )
        composeRule.setContent {
            TravelAssistantTheme(dynamicColor = false) {
                ItineraryScreen(
                    uiState = uiState,
                    onCitySelected = {},
                    onLocalDateChanged = {},
                    onStartTimeChanged = {},
                    onEndTimeChanged = {},
                    onMaximumStopsChanged = {},
                    onNotesChanged = {},
                    onGenerate = {},
                    onCancelGeneration = { cancelled = true },
                    onRetry = { retried = true },
                    onSave = {},
                )
            }
        }
        composeRule.onNodeWithText(getString(R.string.itinerary_loading)).assertExists()
        composeRule.onNodeWithText(getString(R.string.itinerary_cancel_generation))
            .performScrollTo()
            .performClick()
        assertTrue(cancelled)

        composeRule.runOnUiThread {
            uiState = ItineraryUiState(
                generationState = ItineraryGenerationUiState.Error(
                    ItineraryDraftFailure.TIMEOUT,
                ),
            )
        }
        composeRule.onNodeWithText(getString(R.string.itinerary_retry))
            .performScrollTo()
            .performClick()
        assertTrue(retried)

        composeRule.runOnUiThread {
            uiState = ItineraryUiState(
                generationState = ItineraryGenerationUiState.Unavailable,
            )
        }
        composeRule.onNodeWithText(getString(R.string.itinerary_transport_unavailable))
            .assertExists()
    }

    @Test
    fun timelineRendersChronologyDraftLabelAssumptionsWarningsAndAccessibleStops() {
        val draft = draft()
        setItineraryContent(
            ItineraryUiState(
                generationState = ItineraryGenerationUiState.Content(draft),
            ),
        )

        composeRule.onNodeWithTag(ITINERARY_TIMELINE_TEST_TAG)
            .performScrollTo()
            .assertIsDisplayed()
            .assert(hasContentDescription("Dòng thời gian lịch trình nháp"))
        composeRule.onNodeWithText(getString(R.string.itinerary_draft_only))
            .assertExists()
        composeRule.onNodeWithText("09:00–12:00").assertExists()
        composeRule.onNodeWithText("12:00–17:00").assertExists()
        composeRule.onNodeWithText("Bưu điện Trung tâm Sài Gòn").assertExists()
        composeRule.onNodeWithText("Bảo tàng Chứng tích Chiến tranh").assertExists()
        composeRule.onNodeWithText("• Chưa tính thời gian di chuyển.").assertExists()
        composeRule.onNodeWithText("• Hãy kiểm tra giờ mở cửa.").assertExists()
        composeRule.onNode(
            hasContentDescription(
                "Điểm dừng 1: Bưu điện Trung tâm Sài Gòn, 09:00 đến 12:00",
            ),
        ).assertExists()
    }

    @Test
    fun saveCallbackOccursOnlyAfterTapAndUnavailableMessageIsTruthful() {
        var saveCount = 0
        var uiState by mutableStateOf(
            ItineraryUiState(
                generationState = ItineraryGenerationUiState.Content(draft()),
            ),
        )
        composeRule.setContent {
            TravelAssistantTheme(dynamicColor = false) {
                ItineraryScreen(
                    uiState = uiState,
                    onCitySelected = {},
                    onLocalDateChanged = {},
                    onStartTimeChanged = {},
                    onEndTimeChanged = {},
                    onMaximumStopsChanged = {},
                    onNotesChanged = {},
                    onGenerate = {},
                    onCancelGeneration = {},
                    onRetry = {},
                    onSave = { saveCount += 1 },
                )
            }
        }

        assertEquals(0, saveCount)
        composeRule.onNodeWithTag(ITINERARY_SAVE_TEST_TAG)
            .performScrollTo()
            .assertIsEnabled()
            .performClick()
        assertEquals(1, saveCount)

        composeRule.runOnUiThread {
            uiState = uiState.copy(
                saveState = ItinerarySaveUiState.PersistenceUnavailable,
            )
        }
        composeRule.onNodeWithText(getString(R.string.itinerary_persistence_unavailable))
            .assertExists()
        composeRule.onNodeWithText(getString(R.string.itinerary_saved))
            .assertDoesNotExist()
    }

    private fun setItineraryContent(uiState: ItineraryUiState) {
        composeRule.setContent {
            TravelAssistantTheme(dynamicColor = false) {
                ItineraryScreen(
                    uiState = uiState,
                    onCitySelected = {},
                    onLocalDateChanged = {},
                    onStartTimeChanged = {},
                    onEndTimeChanged = {},
                    onMaximumStopsChanged = {},
                    onNotesChanged = {},
                    onGenerate = {},
                    onCancelGeneration = {},
                    onRetry = {},
                    onSave = {},
                )
            }
        }
    }

    private fun draft() = ItineraryDraft(
        city = ItineraryCity.HO_CHI_MINH_CITY,
        localDate = LocalDate.of(2026, 8, 1),
        timezone = "Asia/Ho_Chi_Minh",
        startLocalTime = LocalTime.of(9, 0),
        endLocalTime = LocalTime.of(17, 0),
        items = listOf(
            ItineraryDraftItem(
                title = "Bưu điện Trung tâm Sài Gòn",
                startLocalTime = LocalTime.of(9, 0),
                endLocalTime = LocalTime.of(12, 0),
            ),
            ItineraryDraftItem(
                title = "Bảo tàng Chứng tích Chiến tranh",
                startLocalTime = LocalTime.of(12, 0),
                endLocalTime = LocalTime.of(17, 0),
            ),
        ),
        assumptions = listOf("Chưa tính thời gian di chuyển."),
        warnings = listOf(ItineraryDraftWarning("Hãy kiểm tra giờ mở cửa.")),
    )

    private fun getString(resourceId: Int): String =
        ApplicationProvider.getApplicationContext<android.content.Context>()
            .getString(resourceId)
}
