package com.kltn.travelassistant.feature.assistant.presentation

import androidx.annotation.StringRes
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalFocusManager
import androidx.compose.ui.platform.LocalSoftwareKeyboardController
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.ui.semantics.semantics
import com.kltn.travelassistant.R
import com.kltn.travelassistant.feature.assistant.domain.SpeechRecognitionFailure
import com.kltn.travelassistant.ui.theme.AppSpacing

@Composable
fun AssistantScreen(
    uiState: AssistantUiState,
    isOffline: Boolean,
    onQueryChanged: (String) -> Unit,
    onVoiceInput: () -> Unit,
    onCancelVoiceInput: () -> Unit,
    onConfirmTranscript: () -> Unit,
    onOpenPermissionSettings: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val focusManager = LocalFocusManager.current
    val keyboardController = LocalSoftwareKeyboardController.current

    LazyColumn(
        modifier = modifier.fillMaxSize(),
        contentPadding = PaddingValues(AppSpacing.screen),
        verticalArrangement = Arrangement.spacedBy(AppSpacing.content),
    ) {
        item {
            Text(
                text = stringResource(R.string.destination_assistant),
                modifier = Modifier.semantics { heading() },
                style = MaterialTheme.typography.headlineMedium,
            )
        }
        item {
            Text(
                text = stringResource(R.string.assistant_input_explanation),
                style = MaterialTheme.typography.bodyLarge,
            )
        }
        if (isOffline) {
            item {
                Text(
                    text = stringResource(R.string.assistant_offline_explanation),
                    color = MaterialTheme.colorScheme.error,
                    style = MaterialTheme.typography.bodyMedium,
                )
            }
        }
        item {
            OutlinedTextField(
                value = uiState.queryText,
                onValueChange = onQueryChanged,
                modifier = Modifier.fillMaxWidth(),
                label = { Text(text = stringResource(R.string.assistant_query_label)) },
                placeholder = {
                    Text(text = stringResource(R.string.assistant_query_placeholder))
                },
                minLines = 3,
                maxLines = 6,
            )
        }
        item {
            SpeechInputControls(
                state = uiState.speechInputState,
                onVoiceInput = {
                    focusManager.clearFocus(force = true)
                    keyboardController?.hide()
                    onVoiceInput()
                },
                onCancelVoiceInput = onCancelVoiceInput,
                onOpenPermissionSettings = onOpenPermissionSettings,
            )
        }
        item {
            Text(
                text = stringResource(R.string.assistant_audio_privacy),
                style = MaterialTheme.typography.bodySmall,
            )
        }
        item {
            Button(
                onClick = onConfirmTranscript,
                enabled = uiState.queryText.isNotBlank() &&
                    !uiState.speechInputState.isRecognitionActive,
            ) {
                Text(text = stringResource(R.string.assistant_confirm_transcript))
            }
        }
        uiState.confirmedTranscript?.let {
            item {
                Text(
                    text = stringResource(R.string.assistant_confirmed_local),
                    color = MaterialTheme.colorScheme.primary,
                    style = MaterialTheme.typography.bodyMedium,
                )
            }
        }
    }
}

@Composable
private fun SpeechInputControls(
    state: SpeechInputUiState,
    onVoiceInput: () -> Unit,
    onCancelVoiceInput: () -> Unit,
    onOpenPermissionSettings: () -> Unit,
) {
    Column(
        modifier = Modifier.fillMaxWidth(),
        verticalArrangement = Arrangement.spacedBy(AppSpacing.content),
    ) {
        when {
            state.isRecognitionActive -> {
                OutlinedButton(onClick = onCancelVoiceInput) {
                    Text(text = stringResource(R.string.assistant_voice_cancel))
                }
            }
            else -> {
                Button(
                    onClick = onVoiceInput,
                    enabled = state.canStartVoiceInput,
                ) {
                    Text(text = stringResource(R.string.assistant_voice_start))
                }
            }
        }

        SpeechInputStatus(state)

        if (state is SpeechInputUiState.PermissionDenied && !state.canRequestPermissionAgain) {
            OutlinedButton(onClick = onOpenPermissionSettings) {
                Text(text = stringResource(R.string.assistant_open_permission_settings))
            }
        }
    }
}

@Composable
private fun SpeechInputStatus(state: SpeechInputUiState) {
    val statusRes = state.statusMessageRes ?: return
    if (
        state == SpeechInputUiState.PermissionRequesting ||
        state == SpeechInputUiState.Starting ||
        state == SpeechInputUiState.Processing
    ) {
        CircularProgressIndicator()
    }
    Text(
        text = stringResource(statusRes),
        modifier = Modifier.semantics { liveRegion = LiveRegionMode.Polite },
        color = if (
            state == SpeechInputUiState.Unavailable ||
            state is SpeechInputUiState.PermissionDenied ||
            state is SpeechInputUiState.Error
        ) {
            MaterialTheme.colorScheme.error
        } else {
            MaterialTheme.colorScheme.onSurface
        },
        style = MaterialTheme.typography.bodyMedium,
    )
}

private val SpeechInputUiState.canStartVoiceInput: Boolean
    get() = when (this) {
        SpeechInputUiState.PermissionRequesting,
        SpeechInputUiState.Unavailable,
        -> false
        is SpeechInputUiState.PermissionDenied -> canRequestPermissionAgain
        else -> !isRecognitionActive
    }

private val SpeechInputUiState.statusMessageRes: Int?
    @StringRes get() = when (this) {
        SpeechInputUiState.Idle -> null
        SpeechInputUiState.PermissionRequesting -> R.string.assistant_voice_permission_requesting
        SpeechInputUiState.Starting -> R.string.assistant_voice_starting
        SpeechInputUiState.Ready -> R.string.assistant_voice_ready
        is SpeechInputUiState.Listening -> if (hasPartialTranscript) {
            R.string.assistant_voice_partial
        } else {
            R.string.assistant_voice_listening
        }
        SpeechInputUiState.Processing -> R.string.assistant_voice_processing
        SpeechInputUiState.Completed -> R.string.assistant_voice_completed
        SpeechInputUiState.Cancelled -> R.string.assistant_voice_cancelled
        SpeechInputUiState.Unavailable -> R.string.assistant_voice_unavailable
        is SpeechInputUiState.PermissionDenied -> R.string.assistant_voice_permission_denied
        is SpeechInputUiState.Error -> reason.messageRes
    }

private val SpeechRecognitionFailure.messageRes: Int
    @StringRes get() = when (this) {
        SpeechRecognitionFailure.SERVICE_UNAVAILABLE -> R.string.assistant_voice_unavailable
        SpeechRecognitionFailure.PERMISSION_DENIED -> R.string.assistant_voice_permission_denied
        SpeechRecognitionFailure.NO_SPEECH -> R.string.assistant_voice_error_no_speech
        SpeechRecognitionFailure.NO_MATCH -> R.string.assistant_voice_error_no_match
        SpeechRecognitionFailure.NETWORK -> R.string.assistant_voice_error_network
        SpeechRecognitionFailure.AUDIO -> R.string.assistant_voice_error_audio
        SpeechRecognitionFailure.BUSY -> R.string.assistant_voice_error_busy
        SpeechRecognitionFailure.LANGUAGE_UNAVAILABLE ->
            R.string.assistant_voice_error_language
        SpeechRecognitionFailure.SERVICE -> R.string.assistant_voice_error_service
        SpeechRecognitionFailure.CLIENT -> R.string.assistant_voice_error_client
    }
