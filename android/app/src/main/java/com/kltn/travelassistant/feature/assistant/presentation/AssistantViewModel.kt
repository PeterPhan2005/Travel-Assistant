package com.kltn.travelassistant.feature.assistant.presentation

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.kltn.travelassistant.feature.assistant.domain.AssistantIntentAnalytics
import com.kltn.travelassistant.feature.assistant.domain.AssistantIntentInputMode
import com.kltn.travelassistant.feature.assistant.domain.AssistantIntentOutcome
import com.kltn.travelassistant.feature.assistant.domain.AssistantLocationSnapshot
import com.kltn.travelassistant.feature.assistant.domain.AssistantQueryFailure
import com.kltn.travelassistant.feature.assistant.domain.AssistantQueryRepository
import com.kltn.travelassistant.feature.assistant.domain.AssistantQueryRequest
import com.kltn.travelassistant.feature.assistant.domain.AssistantRepositoryResult
import com.kltn.travelassistant.feature.assistant.domain.AssistantResultStatus
import com.kltn.travelassistant.feature.assistant.domain.MAX_ASSISTANT_SUBMISSION_CODE_POINTS
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
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Job
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

@HiltViewModel
class AssistantViewModel @Inject constructor(
    private val speechRecognitionEngine: SpeechRecognitionEngine,
    private val queryRepository: AssistantQueryRepository,
    private val intentAnalytics: AssistantIntentAnalytics,
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
    private var submissionJob: Job? = null
    private var submissionGeneration = 0L
    private var retrySnapshot: AssistantQueryRequest? = null
    private var queryInputMode = AssistantIntentInputMode.MANUAL
    private var retryInputMode = AssistantIntentInputMode.MANUAL

    fun onQueryChanged(query: String) {
        val wasRecognitionActive = mutableUiState.value.speechInputState.isRecognitionActive
        if (activeVoiceAttemptId != null || wasRecognitionActive) {
            invalidateCurrentAttempt(cancelEngine = wasRecognitionActive)
        }
        cancelActiveSubmission(showCancelled = false)
        retrySnapshot = null
        queryInputMode = AssistantIntentInputMode.MANUAL
        mutableUiState.update { state ->
            state.copy(
                queryText = boundAssistantQueryText(query),
                speechInputState = availableIdleState(),
                confirmedTranscript = null,
                querySubmissionState = AssistantSubmissionUiState.Idle,
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
        if (hadPendingAttempt || wasRecognitionActive) {
            invalidateCurrentAttempt(cancelEngine = wasRecognitionActive)
            updateSpeechState(SpeechInputUiState.Cancelled)
        }
        cancelActiveSubmission(showCancelled = true)
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

    fun submitQuery(
        isOnline: Boolean,
        location: AssistantLocationSnapshot?,
    ) {
        if (submissionJob?.isActive == true) return
        val confirmed = normalizeConfirmedAssistantQuery(
            mutableUiState.value.queryText,
        )
        if (confirmed.isBlank()) return
        if (
            confirmed.codePointCount(0, confirmed.length) >
            MAX_ASSISTANT_SUBMISSION_CODE_POINTS
        ) {
            mutableUiState.update { state ->
                state.copy(
                    confirmedTranscript = null,
                    querySubmissionState = AssistantSubmissionUiState.QueryTooLong,
                )
            }
            return
        }
        val snapshot = AssistantQueryRequest(
            text = confirmed,
            location = location,
        )
        retrySnapshot = snapshot
        retryInputMode = queryInputMode
        mutableUiState.update { state ->
            state.copy(
                queryText = confirmed,
                confirmedTranscript = confirmed,
            )
        }
        if (!isOnline) {
            updateSubmissionState(AssistantSubmissionUiState.Offline)
            return
        }
        execute(snapshot, retryInputMode)
    }

    fun retryQuery(isOnline: Boolean) {
        if (submissionJob?.isActive == true) return
        val snapshot = retrySnapshot ?: return
        if (!mutableUiState.value.querySubmissionState.canRetry) return
        if (!isOnline) {
            updateSubmissionState(AssistantSubmissionUiState.Offline)
            return
        }
        execute(snapshot, retryInputMode)
    }

    fun cancelQuery() {
        cancelActiveSubmission(showCancelled = true)
    }

    fun onAppBackgrounded() {
        onAssistantScreenLeft()
    }

    override fun onCleared() {
        cancelActiveSubmission(showCancelled = false)
        invalidateCurrentAttempt(cancelEngine = false)
        speechRecognitionEngine.close()
        super.onCleared()
    }

    private fun execute(
        snapshot: AssistantQueryRequest,
        inputMode: AssistantIntentInputMode,
    ) {
        val generation = ++submissionGeneration
        updateSubmissionState(AssistantSubmissionUiState.Loading)
        submissionJob = viewModelScope.launch {
            val repositoryResult = try {
                queryRepository.submit(snapshot)
            } catch (exception: CancellationException) {
                throw exception
            } catch (_: Exception) {
                AssistantRepositoryResult.Failure(
                    AssistantQueryFailure.INVALID_RESPONSE,
                )
            }
            if (generation != submissionGeneration) return@launch
            submissionJob = null
            when (repositoryResult) {
                is AssistantRepositoryResult.Structured -> {
                    val result = repositoryResult.result
                    val state = when (result.status) {
                        AssistantResultStatus.SUCCESS ->
                            AssistantSubmissionUiState.Success(result)
                        AssistantResultStatus.PARTIAL ->
                            AssistantSubmissionUiState.Partial(result)
                        AssistantResultStatus.FAILED ->
                            AssistantSubmissionUiState.Failed(result)
                    }
                    updateSubmissionState(state)
                    result.intent?.let { intent ->
                        intentAnalytics.record(
                            intent = intent,
                            outcome = when (result.status) {
                                AssistantResultStatus.SUCCESS ->
                                    AssistantIntentOutcome.SUCCESS
                                AssistantResultStatus.PARTIAL ->
                                    AssistantIntentOutcome.PARTIAL
                                AssistantResultStatus.FAILED ->
                                    AssistantIntentOutcome.FAILED
                            },
                            inputMode = inputMode,
                        )
                    }
                }
                is AssistantRepositoryResult.Failure -> {
                    updateSubmissionState(
                        repositoryResult.reason.toSubmissionState(),
                    )
                }
            }
        }
    }

    private fun cancelActiveSubmission(showCancelled: Boolean) {
        val active = submissionJob?.isActive == true
        if (!active) return
        submissionGeneration += 1
        submissionJob?.cancel()
        submissionJob = null
        if (showCancelled) {
            updateSubmissionState(AssistantSubmissionUiState.Cancelled)
        }
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
                queryInputMode = AssistantIntentInputMode.VOICE
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
                    queryInputMode = AssistantIntentInputMode.VOICE
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

    private fun updateSubmissionState(
        querySubmissionState: AssistantSubmissionUiState,
    ) {
        mutableUiState.update { state ->
            state.copy(querySubmissionState = querySubmissionState)
        }
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

private fun AssistantQueryFailure.toSubmissionState(): AssistantSubmissionUiState =
    when (this) {
        AssistantQueryFailure.OFFLINE -> AssistantSubmissionUiState.Offline
        AssistantQueryFailure.AUTHENTICATION_REQUIRED ->
            AssistantSubmissionUiState.AuthenticationRequired
        AssistantQueryFailure.TIMEOUT,
        AssistantQueryFailure.RATE_LIMITED,
        AssistantQueryFailure.UNAVAILABLE,
        -> AssistantSubmissionUiState.Error(this, retryable = true)
        AssistantQueryFailure.CONFIGURATION,
        AssistantQueryFailure.INVALID_REQUEST,
        AssistantQueryFailure.INVALID_RESPONSE,
        -> AssistantSubmissionUiState.Error(this, retryable = false)
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
