package com.kltn.travelassistant.feature.assistant.presentation

import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.assertIsEnabled
import androidx.compose.ui.test.assertIsFocused
import androidx.compose.ui.test.assertIsNotEnabled
import androidx.compose.ui.test.assertIsNotFocused
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performTextInput
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.kltn.travelassistant.R
import com.kltn.travelassistant.feature.assistant.domain.AssistantIntent
import com.kltn.travelassistant.feature.assistant.domain.AssistantPoiResult
import com.kltn.travelassistant.feature.assistant.domain.AssistantQueryResult
import com.kltn.travelassistant.feature.assistant.domain.AssistantResultStatus
import com.kltn.travelassistant.feature.assistant.domain.AssistantWarning
import com.kltn.travelassistant.feature.assistant.domain.SpeechRecognitionFailure
import com.kltn.travelassistant.ui.theme.TravelAssistantTheme
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class AssistantScreenTest {
    @get:Rule
    val composeRule = createComposeRule()

    @Test
    fun manualInputUsesOneExplicitSendActionAndRemainsEditable() {
        var changedText = ""
        var confirmationRequested = false
        var submissionRequested = false
        setAssistantContent(
            uiState = AssistantUiState(queryText = "Tôi muốn ăn phở"),
            onQueryChanged = { changedText = it },
            onConfirmTranscript = { confirmationRequested = true },
            onSubmitQuery = { submissionRequested = true },
        )

        composeRule.onNodeWithText(getString(R.string.assistant_query_label))
            .assertIsEnabled()
            .performTextInput(" gần đây")
        assertTrue(changedText.contains("gần đây"))

        composeRule.onNodeWithText(getString(R.string.assistant_send_query))
            .assertIsEnabled()
            .performClick()
        assertTrue(confirmationRequested)
        assertTrue(submissionRequested)
    }

    @Test
    fun overlongInputShowsFixedLocalErrorAndCannotSubmit() {
        setAssistantContent(
            uiState = AssistantUiState(queryText = "a".repeat(501)),
        )

        composeRule.onNodeWithText(getString(R.string.assistant_request_too_long))
            .assertIsDisplayed()
        composeRule.onNodeWithText(getString(R.string.assistant_send_query))
            .assertIsNotEnabled()
    }

    @Test
    fun voiceActionClearsEditorFocusAndTypingNeverInvokesApplicationRecognition() {
        var changedText = ""
        var voiceRequestCount = 0
        setAssistantContent(
            uiState = AssistantUiState(),
            onQueryChanged = { changedText = it },
            onVoiceInput = { voiceRequestCount += 1 },
        )
        val editor = composeRule.onNodeWithText(
            getString(R.string.assistant_query_label),
        )

        editor
            .performClick()
            .assertIsFocused()
            .performTextInput("Tôi muốn tìm quán phở")

        assertTrue(changedText.contains("Tôi muốn tìm quán phở"))
        assertTrue(voiceRequestCount == 0)

        composeRule.onNodeWithText(getString(R.string.assistant_voice_start))
            .performClick()

        assertTrue(voiceRequestCount == 1)
        editor.assertIsNotFocused()
    }

    @Test
    fun partialTranscriptAndExplicitCancellationAreVisible() {
        var cancellationRequested = false
        setAssistantContent(
            uiState = AssistantUiState(
                queryText = "tôi muốn ăn",
                speechInputState = SpeechInputUiState.Listening(
                    hasPartialTranscript = true,
                ),
            ),
            onCancelVoiceInput = { cancellationRequested = true },
        )

        composeRule.onNodeWithText("tôi muốn ăn").assertIsDisplayed()
        composeRule.onNodeWithText(getString(R.string.assistant_voice_partial))
            .assertIsDisplayed()
        composeRule.onNodeWithText(getString(R.string.assistant_voice_cancel))
            .assertIsDisplayed()
            .performClick()
        assertTrue(cancellationRequested)
        composeRule.onNodeWithText(getString(R.string.assistant_send_query))
            .assertIsNotEnabled()
    }

    @Test
    fun noSpeechKeepsEditableTextAndOffersExplicitVoiceRetry() {
        var retryCount = 0
        setAssistantContent(
            uiState = AssistantUiState(
                queryText = "Nội dung vẫn giữ lại",
                speechInputState = SpeechInputUiState.Error(
                    SpeechRecognitionFailure.NO_SPEECH,
                ),
            ),
            onVoiceInput = { retryCount += 1 },
        )

        composeRule.onNodeWithText("Nội dung vẫn giữ lại")
            .assertIsDisplayed()
            .assertIsEnabled()
        composeRule.onNodeWithText(getString(R.string.assistant_voice_error_no_speech))
            .assertIsDisplayed()
        composeRule.onNodeWithText(getString(R.string.assistant_voice_start))
            .assertIsEnabled()
            .performClick()

        assertTrue(retryCount == 1)
    }

    @Test
    fun finalTranscriptCanBeEditedBeforeConfirmation() {
        var changedText = ""
        setAssistantContent(
            uiState = AssistantUiState(
                queryText = "Tôi muốn ăn phở gần đây",
                speechInputState = SpeechInputUiState.Completed,
            ),
            onQueryChanged = { changedText = it },
        )

        composeRule.onNodeWithText(getString(R.string.assistant_voice_completed))
            .assertIsDisplayed()
        composeRule.onNodeWithText(getString(R.string.assistant_query_label))
            .assertIsEnabled()
            .performTextInput(" vào buổi sáng")

        assertTrue(changedText.contains("vào buổi sáng"))
    }

    @Test
    fun unavailableVoiceLeavesManualTextEnabled() {
        setAssistantContent(
            uiState = AssistantUiState(
                speechInputState = SpeechInputUiState.Unavailable,
            ),
        )

        composeRule.onNodeWithText(getString(R.string.assistant_voice_unavailable))
            .assertIsDisplayed()
        composeRule.onNodeWithText(getString(R.string.assistant_voice_start))
            .assertIsNotEnabled()
        composeRule.onNodeWithText(getString(R.string.assistant_query_label))
            .assertIsEnabled()
    }

    @Test
    fun permanentPermissionDenialOffersApplicationSettings() {
        var settingsRequested = false
        setAssistantContent(
            uiState = AssistantUiState(
                speechInputState = SpeechInputUiState.PermissionDenied(
                    canRequestPermissionAgain = false,
                ),
            ),
            onOpenPermissionSettings = { settingsRequested = true },
        )

        composeRule.onNodeWithText(getString(R.string.assistant_voice_permission_denied))
            .assertIsDisplayed()
        composeRule.onNodeWithText(getString(R.string.assistant_voice_start))
            .assertIsNotEnabled()
        composeRule.onNodeWithText(getString(R.string.assistant_open_permission_settings))
            .assertIsDisplayed()
            .performClick()
        assertTrue(settingsRequested)
    }

    @Test
    fun settingsReturnEnablesVoiceButtonWithoutAutomaticallyStartingListening() {
        var uiState by mutableStateOf(
            AssistantUiState(
                speechInputState = SpeechInputUiState.PermissionDenied(
                    canRequestPermissionAgain = false,
                ),
            ),
        )
        var voiceRequestCount = 0
        composeRule.setContent {
            TravelAssistantTheme(dynamicColor = false) {
                AssistantScreen(
                    uiState = uiState,
                    isOffline = false,
                    onQueryChanged = {},
                    onVoiceInput = { voiceRequestCount += 1 },
                    onCancelVoiceInput = {},
                    onConfirmTranscript = {},
                    onOpenPermissionSettings = {},
                )
            }
        }
        val voiceButton = composeRule.onNodeWithText(
            getString(R.string.assistant_voice_start),
        )
        voiceButton.assertIsNotEnabled()

        composeRule.runOnUiThread {
            uiState = uiState.copy(speechInputState = SpeechInputUiState.Idle)
        }

        voiceButton.assertIsEnabled()
        assertTrue(voiceRequestCount == 0)
        voiceButton.performClick()
        assertTrue(voiceRequestCount == 1)
    }

    @Test
    fun recognitionErrorAndSendActionAreExplicit() {
        setAssistantContent(
            uiState = AssistantUiState(
                queryText = "Đi đâu hôm nay?",
                speechInputState = SpeechInputUiState.Error(
                    SpeechRecognitionFailure.NO_MATCH,
                ),
                confirmedTranscript = "Đi đâu hôm nay?",
            ),
        )

        composeRule.onNodeWithText(getString(R.string.assistant_voice_error_no_match))
            .assertIsDisplayed()
        composeRule.onNodeWithText(getString(R.string.assistant_send_query))
            .assertIsEnabled()
    }

    @Test
    fun privacyTextNamesSelectedDeviceServiceNetworkPossibilityAndTemporaryTranscript() {
        setAssistantContent(uiState = AssistantUiState())
        val privacyText = getString(R.string.assistant_audio_privacy)

        composeRule.onNodeWithText(privacyText).assertIsDisplayed()
        assertTrue(privacyText.contains("không ghi âm giọng nói vào tệp"))
        assertTrue(privacyText.contains("không lưu trữ hoặc tải âm thanh lên"))
        assertTrue(privacyText.contains("dịch vụ nhận dạng giọng nói được chọn trên thiết bị"))
        assertTrue(privacyText.contains("có thể dùng mạng"))
        assertTrue(privacyText.contains("Chỉ văn bản"))
        assertTrue(privacyText.contains("đã được bạn chỉnh sửa"))
        assertTrue(privacyText.contains("đi tới máy chủ trợ lý"))
    }

    @Test
    fun loadingCancelOfflineAndAuthenticationStatesAreVisible() {
        var cancelled = false
        var uiState by mutableStateOf(
            AssistantUiState(
                queryText = "Câu hỏi",
                querySubmissionState = AssistantSubmissionUiState.Loading,
            ),
        )
        composeRule.setContent {
            TravelAssistantTheme(dynamicColor = false) {
                AssistantScreen(
                    uiState = uiState,
                    isOffline = false,
                    onQueryChanged = {},
                    onVoiceInput = {},
                    onCancelVoiceInput = {},
                    onConfirmTranscript = {},
                    onCancelQuery = { cancelled = true },
                    onOpenPermissionSettings = {},
                )
            }
        }
        composeRule.onNodeWithText(getString(R.string.assistant_request_loading))
            .assertIsDisplayed()
        composeRule.onNodeWithText(getString(R.string.assistant_cancel_request))
            .performClick()
        assertTrue(cancelled)

        composeRule.runOnUiThread {
            uiState = AssistantUiState(
                queryText = "Câu hỏi",
                querySubmissionState = AssistantSubmissionUiState.Offline,
            )
        }
        composeRule.onNodeWithText(getString(R.string.assistant_request_offline))
            .assertIsDisplayed()

        composeRule.runOnUiThread {
            uiState = AssistantUiState(
                queryText = "Câu hỏi",
                querySubmissionState = AssistantSubmissionUiState.AuthenticationRequired,
            )
        }
        composeRule.onNodeWithText(getString(R.string.assistant_request_auth_required))
            .assertIsDisplayed()
    }

    @Test
    fun structuredPartialRendersMessagePoiPresentFieldsAndWarningOnly() {
        val result = AssistantQueryResult(
            status = AssistantResultStatus.PARTIAL,
            intent = AssistantIntent.NEARBY_DISCOVERY,
            message = "Kết quả đã được kiểm tra",
            poiResults = listOf(
                AssistantPoiResult(
                    name = "Phở Một",
                    category = "Nhà hàng",
                    address = null,
                    distanceMetres = 1_250.0,
                    rating = 4.5,
                    ratingCount = null,
                    price = null,
                    openingHoursSummary = null,
                ),
            ),
            narration = null,
            itinerary = null,
            sources = emptyList(),
            warnings = listOf(
                AssistantWarning(
                    message = "Một phần dữ liệu chưa thể xác nhận.",
                    retryable = true,
                ),
            ),
            retryable = true,
        )
        var retried = false
        setAssistantContent(
            uiState = AssistantUiState(
                queryText = "Câu hỏi",
                querySubmissionState = AssistantSubmissionUiState.Partial(result),
            ),
            onRetryQuery = { retried = true },
        )

        composeRule.onNodeWithText("Kết quả đã được kiểm tra").assertIsDisplayed()
        composeRule.onNodeWithText("Phở Một").assertIsDisplayed()
        composeRule.onNodeWithText("1,3 km").assertIsDisplayed()
        composeRule.onNodeWithText("4,5 ★").assertIsDisplayed()
        composeRule.onNodeWithText("Một phần dữ liệu chưa thể xác nhận.")
            .assertIsDisplayed()
        composeRule.onNodeWithText(getString(R.string.assistant_retry_request))
            .performClick()
        assertTrue(retried)
    }

    private fun setAssistantContent(
        uiState: AssistantUiState,
        onQueryChanged: (String) -> Unit = {},
        onVoiceInput: () -> Unit = {},
        onCancelVoiceInput: () -> Unit = {},
        onConfirmTranscript: () -> Unit = {},
        onSubmitQuery: () -> Unit = {},
        onCancelQuery: () -> Unit = {},
        onRetryQuery: () -> Unit = {},
        onOpenPermissionSettings: () -> Unit = {},
    ) {
        composeRule.setContent {
            TravelAssistantTheme(dynamicColor = false) {
                AssistantScreen(
                    uiState = uiState,
                    isOffline = false,
                    onQueryChanged = onQueryChanged,
                    onVoiceInput = onVoiceInput,
                    onCancelVoiceInput = onCancelVoiceInput,
                    onConfirmTranscript = onConfirmTranscript,
                    onSubmitQuery = onSubmitQuery,
                    onCancelQuery = onCancelQuery,
                    onRetryQuery = onRetryQuery,
                    onOpenPermissionSettings = onOpenPermissionSettings,
                )
            }
        }
    }

    private fun getString(resourceId: Int): String =
        ApplicationProvider.getApplicationContext<android.content.Context>()
            .getString(resourceId)
}
