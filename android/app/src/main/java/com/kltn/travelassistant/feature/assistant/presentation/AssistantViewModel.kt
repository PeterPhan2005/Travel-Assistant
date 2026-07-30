package com.kltn.travelassistant.feature.assistant.presentation

import androidx.lifecycle.ViewModel
import com.kltn.travelassistant.feature.assistant.domain.boundAssistantQueryText
import com.kltn.travelassistant.feature.assistant.domain.normalizeConfirmedAssistantQuery
import com.kltn.travelassistant.feature.assistant.domain.normalizeRecognizedAssistantQuery
import com.kltn.travelassistant.feature.assistant.domain.SpeechRecognitionEngine
import com.kltn.travelassistant.feature.assistant.domain.SpeechRecognitionEvent
import com.kltn.travelassistant.feature.assistant.domain.SpeechRecognitionFailure
import com.kltn.travelassistant.feature.assistant.domain.SpeechRecognitionListener
import com.kltn.travelassistant.feature.assistant.domain.SpeechRecognitionStartResult
import dagger.hilt.android.lifecycle.HiltViewModel
import javax.inject.Inject
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update

@HiltViewModel
class AssistantViewModel @Inject constructor(
    private val speechRecognitionEngine: SpeechRecognitionEngine,
) : ViewModel() {
    private val speechRecognitionAvailable = speechRecognitionEngine.isAvailable()
    private val mutableUiState = MutableStateFlow(
        AssistantUiState(
            speechInputState = if (speechRecognitionAvailable) {
                SpeechInputUiState.Idle
            } else {
                SpeechInputUiState.Unavailable
            },
        ),
    )
    val uiState: StateFlow<AssistantUiState> = mutableUiState.asStateFlow()

    private var acceptsRecognitionEvents = false
    private var activeVoiceAttemptId: Long? = null
    private val attemptIdGenerator = VoiceInputAttemptIdGenerator()

    fun onQueryChanged(query: String) {
        val wasRecognitionActive = mutableUiState.value.speechInputState.isRecognitionActive
        if (activeVoiceAttemptId != null || wasRecognitionActive) {
            invalidateCurrentAttempt(cancelEngine = wasRecognitionActive)
        }
        mutableUiState.update { state ->
            state.copy(
                queryText = boundAssistantQueryText(query),
                speechInputState = availableIdleState(),
                confirmedTranscript = null,
            )
        }
    }

    fun beginVoiceInputAttempt(): Long? {
        if (!speechRecognitionAvailable) {
            updateSpeechState(SpeechInputUiState.Unavailable)
            return null
        }
        if (
            activeVoiceAttemptId != null ||
            mutableUiState.value.speechInputState.isRecognitionActive ||
            mutableUiState.value.speechInputState == SpeechInputUiState.PermissionRequesting
        ) {
            return null
        }
        return attemptIdGenerator.next().also { attemptId ->
            activeVoiceAttemptId = attemptId
        }
    }

    fun onMicrophonePermissionRequestStarted(attemptId: Long) {
        if (!isCurrentAttempt(attemptId)) return
        updateSpeechState(SpeechInputUiState.PermissionRequesting)
    }

    fun onMicrophonePermissionGranted(attemptId: Long) {
        if (!isCurrentAttempt(attemptId)) return
        if (mutableUiState.value.speechInputState.isRecognitionActive) return

        mutableUiState.update { state ->
            state.copy(
                speechInputState = SpeechInputUiState.Starting,
                confirmedTranscript = null,
            )
        }
        acceptsRecognitionEvents = true
        val recognitionListener = SpeechRecognitionListener { event ->
            onSpeechRecognitionEvent(attemptId, event)
        }
        when (
            val result = speechRecognitionEngine.start(
                languageTag = VIETNAMESE_LANGUAGE_TAG,
                listener = recognitionListener,
            )
        ) {
            SpeechRecognitionStartResult.Started -> Unit
            is SpeechRecognitionStartResult.Failure -> {
                acceptsRecognitionEvents = false
                activeVoiceAttemptId = null
                applyFailure(result.reason)
            }
        }
    }

    fun onMicrophonePermissionDenied(
        attemptId: Long,
        canRequestPermissionAgain: Boolean,
    ) {
        if (!isCurrentAttempt(attemptId)) return
        acceptsRecognitionEvents = false
        activeVoiceAttemptId = null
        updateSpeechState(
            SpeechInputUiState.PermissionDenied(
                canRequestPermissionAgain = canRequestPermissionAgain,
            ),
        )
    }

    fun onMicrophonePermissionStatusRefreshed(isGranted: Boolean) {
        if (
            isGranted &&
            mutableUiState.value.speechInputState is SpeechInputUiState.PermissionDenied
        ) {
            updateSpeechState(availableIdleState())
        }
    }

    fun cancelSpeechRecognition() {
        val hadPendingAttempt = activeVoiceAttemptId != null
        val wasRecognitionActive = mutableUiState.value.speechInputState.isRecognitionActive
        if (!hadPendingAttempt && !wasRecognitionActive) return
        invalidateCurrentAttempt(cancelEngine = wasRecognitionActive)
        updateSpeechState(SpeechInputUiState.Cancelled)
    }

    fun onAssistantScreenLeft() {
        val hadPendingAttempt = activeVoiceAttemptId != null
        val wasRecognitionActive = mutableUiState.value.speechInputState.isRecognitionActive
        if (!hadPendingAttempt && !wasRecognitionActive) return
        invalidateCurrentAttempt(cancelEngine = wasRecognitionActive)
        updateSpeechState(SpeechInputUiState.Cancelled)
    }

    fun confirmTranscript() {
        if (mutableUiState.value.speechInputState.isRecognitionActive) return
        val confirmed = normalizeConfirmedAssistantQuery(mutableUiState.value.queryText)
        if (confirmed.isEmpty()) return
        mutableUiState.update { state ->
            state.copy(
                queryText = confirmed,
                confirmedTranscript = confirmed,
            )
        }
    }

    override fun onCleared() {
        invalidateCurrentAttempt(cancelEngine = false)
        speechRecognitionEngine.close()
        super.onCleared()
    }

    private fun onSpeechRecognitionEvent(
        attemptId: Long,
        event: SpeechRecognitionEvent,
    ) {
        if (!acceptsRecognitionEvents || !isCurrentAttempt(attemptId)) return
        when (event) {
            SpeechRecognitionEvent.Ready -> updateSpeechState(SpeechInputUiState.Ready)
            SpeechRecognitionEvent.Listening -> updateSpeechState(
                SpeechInputUiState.Listening(hasPartialTranscript = false),
            )
            is SpeechRecognitionEvent.PartialTranscript -> {
                val transcript = normalizeRecognizedAssistantQuery(event.text)
                if (transcript.isBlank()) return
                mutableUiState.update { state ->
                    state.copy(
                        queryText = transcript,
                        speechInputState = SpeechInputUiState.Listening(
                            hasPartialTranscript = true,
                        ),
                        confirmedTranscript = null,
                    )
                }
            }
            is SpeechRecognitionEvent.FinalTranscript -> {
                acceptsRecognitionEvents = false
                activeVoiceAttemptId = null
                val transcript = normalizeRecognizedAssistantQuery(event.text)
                if (transcript.isBlank()) {
                    applyFailure(SpeechRecognitionFailure.NO_MATCH)
                } else {
                    mutableUiState.update { state ->
                        state.copy(
                            queryText = transcript,
                            speechInputState = SpeechInputUiState.Completed,
                            confirmedTranscript = null,
                        )
                    }
                }
            }
            SpeechRecognitionEvent.EndOfSpeech ->
                updateSpeechState(SpeechInputUiState.Processing)
            SpeechRecognitionEvent.Cancelled -> {
                acceptsRecognitionEvents = false
                activeVoiceAttemptId = null
                updateSpeechState(SpeechInputUiState.Cancelled)
            }
            is SpeechRecognitionEvent.Failure -> {
                acceptsRecognitionEvents = false
                activeVoiceAttemptId = null
                applyFailure(event.reason)
            }
        }
    }

    private fun applyFailure(failure: SpeechRecognitionFailure) {
        val state = when (failure) {
            SpeechRecognitionFailure.SERVICE_UNAVAILABLE -> SpeechInputUiState.Unavailable
            SpeechRecognitionFailure.PERMISSION_DENIED -> SpeechInputUiState.PermissionDenied(
                canRequestPermissionAgain = true,
            )
            else -> SpeechInputUiState.Error(failure)
        }
        updateSpeechState(state)
    }

    private fun updateSpeechState(speechInputState: SpeechInputUiState) {
        mutableUiState.update { state -> state.copy(speechInputState = speechInputState) }
    }

    private fun availableIdleState(): SpeechInputUiState =
        if (speechRecognitionAvailable) {
            SpeechInputUiState.Idle
        } else {
            SpeechInputUiState.Unavailable
        }

    private fun isCurrentAttempt(attemptId: Long): Boolean =
        activeVoiceAttemptId == attemptId

    private fun invalidateCurrentAttempt(cancelEngine: Boolean) {
        acceptsRecognitionEvents = false
        activeVoiceAttemptId = null
        if (cancelEngine) {
            speechRecognitionEngine.cancel()
        }
    }

    private companion object {
        const val VIETNAMESE_LANGUAGE_TAG = "vi-VN"
    }
}

internal class VoiceInputAttemptIdGenerator(
    private val maximumId: Long = Long.MAX_VALUE,
) {
    private var nextId = 1L

    init {
        require(maximumId > 0L)
    }

    fun next(): Long {
        val result = nextId
        nextId = if (nextId == maximumId) 1L else nextId + 1L
        return result
    }
}
