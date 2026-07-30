package com.kltn.travelassistant.feature.assistant.presentation

import com.kltn.travelassistant.feature.assistant.domain.SpeechRecognitionFailure

data class AssistantUiState(
    val queryText: String = "",
    val speechInputState: SpeechInputUiState = SpeechInputUiState.Idle,
    val confirmedTranscript: String? = null,
)

sealed interface SpeechInputUiState {
    data object Idle : SpeechInputUiState

    data object PermissionRequesting : SpeechInputUiState

    data object Starting : SpeechInputUiState

    data object Ready : SpeechInputUiState

    data class Listening(
        val hasPartialTranscript: Boolean,
    ) : SpeechInputUiState

    data object Processing : SpeechInputUiState

    data object Completed : SpeechInputUiState

    data object Cancelled : SpeechInputUiState

    data object Unavailable : SpeechInputUiState

    data class PermissionDenied(
        val canRequestPermissionAgain: Boolean,
    ) : SpeechInputUiState

    data class Error(
        val reason: SpeechRecognitionFailure,
    ) : SpeechInputUiState
}

internal val SpeechInputUiState.isRecognitionActive: Boolean
    get() = when (this) {
        SpeechInputUiState.Starting,
        SpeechInputUiState.Ready,
        is SpeechInputUiState.Listening,
        SpeechInputUiState.Processing,
        -> true
        SpeechInputUiState.Idle,
        SpeechInputUiState.PermissionRequesting,
        SpeechInputUiState.Completed,
        SpeechInputUiState.Cancelled,
        SpeechInputUiState.Unavailable,
        is SpeechInputUiState.PermissionDenied,
        is SpeechInputUiState.Error,
        -> false
    }
