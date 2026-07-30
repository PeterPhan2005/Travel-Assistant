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
    fun manualInputAndConfirmationActionsRemainLocalAndEditable() {
        var changedText = ""
        var confirmationRequested = false
        setAssistantContent(
            uiState = AssistantUiState(queryText = "Tôi muốn ăn phở"),
            onQueryChanged = { changedText = it },
            onConfirmTranscript = { confirmationRequested = true },
        )

        composeRule.onNodeWithText(getString(R.string.assistant_query_label))
            .assertIsEnabled()
            .performTextInput(" gần đây")
        assertTrue(changedText.contains("gần đây"))

        composeRule.onNodeWithText(getString(R.string.assistant_confirm_transcript))
            .assertIsEnabled()
            .performClick()
        assertTrue(confirmationRequested)
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
        composeRule.onNodeWithText(getString(R.string.assistant_confirm_transcript))
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
    fun recognitionErrorAndLocalConfirmationAreExplicit() {
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
        composeRule.onNodeWithText(getString(R.string.assistant_confirmed_local))
            .assertIsDisplayed()
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
        assertTrue(privacyText.contains("chỉ được giữ tạm thời trên thiết bị"))
        assertTrue(privacyText.contains("có thể chỉnh sửa"))
        assertTrue(privacyText.contains("tính năng gửi được triển khai"))
    }

    private fun setAssistantContent(
        uiState: AssistantUiState,
        onQueryChanged: (String) -> Unit = {},
        onVoiceInput: () -> Unit = {},
        onCancelVoiceInput: () -> Unit = {},
        onConfirmTranscript: () -> Unit = {},
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
                    onOpenPermissionSettings = onOpenPermissionSettings,
                )
            }
        }
    }

    private fun getString(resourceId: Int): String =
        ApplicationProvider.getApplicationContext<android.content.Context>()
            .getString(resourceId)
}
