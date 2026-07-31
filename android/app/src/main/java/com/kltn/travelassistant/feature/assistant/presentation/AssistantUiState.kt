package com.kltn.travelassistant.feature.assistant.presentation

import com.kltn.travelassistant.feature.assistant.domain.SpeechRecognitionFailure
import com.kltn.travelassistant.feature.assistant.domain.AssistantQueryFailure
import com.kltn.travelassistant.feature.assistant.domain.AssistantQueryResult

data class AssistantUiState(
    val queryText: String = "",
    val speechInputState: SpeechInputUiState = SpeechInputUiState.Idle,
    val confirmedTranscript: String? = null,
    val querySubmissionState: AssistantSubmissionUiState =
        AssistantSubmissionUiState.Idle,
)

sealed interface AssistantSubmissionUiState {
    data object Idle : AssistantSubmissionUiState

    data object Loading : AssistantSubmissionUiState

    data class Success(
        val result: AssistantQueryResult,
    ) : AssistantSubmissionUiState

    data class Partial(
        val result: AssistantQueryResult,
    ) : AssistantSubmissionUiState

    data class Failed(
        val result: AssistantQueryResult,
    ) : AssistantSubmissionUiState

    data object Cancelled : AssistantSubmissionUiState

    data object Offline : AssistantSubmissionUiState

    data object AuthenticationRequired : AssistantSubmissionUiState

    data object QueryTooLong : AssistantSubmissionUiState

    data class Error(
        val reason: AssistantQueryFailure,
        val retryable: Boolean,
    ) : AssistantSubmissionUiState
}

internal val AssistantSubmissionUiState.isRequestActive: Boolean
    get() = this == AssistantSubmissionUiState.Loading

internal val AssistantSubmissionUiState.canRetry: Boolean
    get() = when (this) {
        AssistantSubmissionUiState.Offline,
        AssistantSubmissionUiState.AuthenticationRequired,
        -> true
        is AssistantSubmissionUiState.Partial -> result.retryable
        is AssistantSubmissionUiState.Failed -> result.retryable
        is AssistantSubmissionUiState.Error -> retryable
        else -> false
    }

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
