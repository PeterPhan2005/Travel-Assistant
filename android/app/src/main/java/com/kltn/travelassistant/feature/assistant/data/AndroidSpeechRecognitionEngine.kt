package com.kltn.travelassistant.feature.assistant.data

import android.content.Context
import android.content.Intent
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.speech.RecognitionListener
import android.speech.RecognizerIntent
import android.speech.SpeechRecognizer
import com.kltn.travelassistant.feature.assistant.domain.SpeechRecognitionEngine
import com.kltn.travelassistant.feature.assistant.domain.SpeechRecognitionEvent
import com.kltn.travelassistant.feature.assistant.domain.SpeechRecognitionFailure
import com.kltn.travelassistant.feature.assistant.domain.SpeechRecognitionListener
import com.kltn.travelassistant.feature.assistant.domain.SpeechRecognitionStartResult
import dagger.hilt.android.qualifiers.ApplicationContext
import javax.inject.Inject

class AndroidSpeechRecognitionEngine internal constructor(
    private val availabilityChecker: () -> Boolean,
    private val platformFactory: () -> SpeechRecognizerPlatform,
    private val mainThreadChecker: () -> Boolean,
    private val intentFactory: (String) -> Intent,
    private val mainThreadExecutor: ((() -> Unit) -> Unit) = {},
) : SpeechRecognitionEngine {
    @Inject
    constructor(
        @ApplicationContext context: Context,
    ) : this(
        availabilityChecker = { SpeechRecognizer.isRecognitionAvailable(context) },
        platformFactory = {
            AndroidSpeechRecognizerPlatform(
                SpeechRecognizer.createSpeechRecognizer(context),
            )
        },
        mainThreadChecker = { Looper.myLooper() == Looper.getMainLooper() },
        intentFactory = ::createRecognitionIntent,
        mainThreadExecutor = ::runOnAndroidMainThread,
    )

    private var recognizer: SpeechRecognizerPlatform? = null
    private var activeListener: SpeechRecognitionListener? = null
    private var activeSessionId = 0L
    private var isSessionActive = false
    private var isClosed = false

    override fun isAvailable(): Boolean {
        if (isClosed || !mainThreadChecker()) return false
        return try {
            availabilityChecker()
        } catch (_: RuntimeException) {
            false
        }
    }

    override fun start(
        languageTag: String,
        listener: SpeechRecognitionListener,
    ): SpeechRecognitionStartResult {
        if (!mainThreadChecker()) {
            return SpeechRecognitionStartResult.Failure(SpeechRecognitionFailure.CLIENT)
        }
        if (isClosed) {
            return SpeechRecognitionStartResult.Failure(SpeechRecognitionFailure.CLIENT)
        }
        if (isSessionActive) {
            return SpeechRecognitionStartResult.Failure(SpeechRecognitionFailure.BUSY)
        }
        if (!isAvailable()) {
            return SpeechRecognitionStartResult.Failure(
                SpeechRecognitionFailure.SERVICE_UNAVAILABLE,
            )
        }

        val speechRecognizer = try {
            recognizer ?: platformFactory().also {
                recognizer = it
            }
        } catch (_: SecurityException) {
            return SpeechRecognitionStartResult.Failure(
                SpeechRecognitionFailure.PERMISSION_DENIED,
            )
        } catch (_: RuntimeException) {
            return SpeechRecognitionStartResult.Failure(
                SpeechRecognitionFailure.SERVICE_UNAVAILABLE,
            )
        }

        val sessionId = advanceSessionId()
        activeListener = listener
        isSessionActive = true

        return try {
            speechRecognizer.setRecognitionListener(platformListener(sessionId))
            speechRecognizer.startListening(intentFactory(languageTag))
            SpeechRecognitionStartResult.Started
        } catch (_: SecurityException) {
            finishSession(sessionId)
            SpeechRecognitionStartResult.Failure(
                SpeechRecognitionFailure.PERMISSION_DENIED,
            )
        } catch (_: RuntimeException) {
            finishSession(sessionId)
            SpeechRecognitionStartResult.Failure(SpeechRecognitionFailure.SERVICE)
        }
    }

    override fun cancel() {
        if (!mainThreadChecker()) {
            mainThreadExecutor(::cancel)
            return
        }
        if (isClosed || !isSessionActive) return

        val listener = activeListener
        invalidateSession()
        try {
            recognizer?.cancel()
        } catch (_: RuntimeException) {
            // Cancellation remains a controlled local terminal state.
        }
        listener?.onEvent(SpeechRecognitionEvent.Cancelled)
    }

    override fun close() {
        if (!mainThreadChecker()) {
            mainThreadExecutor(::close)
            return
        }
        if (isClosed) return
        isClosed = true
        val platform = recognizer
        val wasSessionActive = isSessionActive
        invalidateSession()
        recognizer = null

        if (wasSessionActive) {
            try {
                platform?.cancel()
            } catch (_: RuntimeException) {
                // The listener is already invalidated and close continues.
            }
        }
        try {
            platform?.destroy()
        } catch (_: RuntimeException) {
            // The feature is already being released; no platform error escapes.
        }
    }

    private fun platformListener(sessionId: Long): RecognitionListener =
        object : RecognitionListener {
            override fun onReadyForSpeech(params: Bundle?) {
                emit(sessionId, SpeechRecognitionEvent.Ready)
            }

            override fun onBeginningOfSpeech() {
                emit(sessionId, SpeechRecognitionEvent.Listening)
            }

            override fun onRmsChanged(rmsdB: Float) = Unit

            override fun onBufferReceived(buffer: ByteArray?) = Unit

            override fun onEndOfSpeech() {
                emit(sessionId, SpeechRecognitionEvent.EndOfSpeech)
            }

            override fun onError(error: Int) {
                emit(
                    sessionId,
                    SpeechRecognitionEvent.Failure(error.toSpeechRecognitionFailure()),
                    terminal = true,
                )
            }

            override fun onResults(results: Bundle?) {
                val transcript = results.firstTranscript()
                if (transcript == null) {
                    emit(
                        sessionId,
                        SpeechRecognitionEvent.Failure(SpeechRecognitionFailure.NO_MATCH),
                        terminal = true,
                    )
                } else {
                    emit(
                        sessionId,
                        SpeechRecognitionEvent.FinalTranscript(transcript),
                        terminal = true,
                    )
                }
            }

            override fun onPartialResults(partialResults: Bundle?) {
                partialResults.firstTranscript()?.let { transcript ->
                    emit(sessionId, SpeechRecognitionEvent.PartialTranscript(transcript))
                }
            }

            override fun onEvent(eventType: Int, params: Bundle?) = Unit
        }

    private fun emit(
        sessionId: Long,
        event: SpeechRecognitionEvent,
        terminal: Boolean = false,
    ) {
        if (!isSessionActive || sessionId != activeSessionId) return
        val listener = activeListener ?: return
        if (terminal) {
            isSessionActive = false
            activeListener = null
        }
        listener.onEvent(event)
    }

    private fun finishSession(sessionId: Long) {
        if (sessionId != activeSessionId) return
        isSessionActive = false
        activeListener = null
    }

    private fun invalidateSession() {
        isSessionActive = false
        activeListener = null
        advanceSessionId()
    }

    private fun advanceSessionId(): Long {
        activeSessionId = if (activeSessionId == Long.MAX_VALUE) {
            1L
        } else {
            activeSessionId + 1L
        }
        return activeSessionId
    }
}

internal interface SpeechRecognizerPlatform {
    fun setRecognitionListener(listener: RecognitionListener)

    fun startListening(intent: Intent)

    fun cancel()

    fun destroy()
}

private class AndroidSpeechRecognizerPlatform(
    private val recognizer: SpeechRecognizer,
) : SpeechRecognizerPlatform {
    override fun setRecognitionListener(listener: RecognitionListener) {
        recognizer.setRecognitionListener(listener)
    }

    override fun startListening(intent: Intent) {
        recognizer.startListening(intent)
    }

    override fun cancel() {
        recognizer.cancel()
    }

    override fun destroy() {
        recognizer.destroy()
    }
}

internal fun createRecognitionIntent(languageTag: String): Intent =
    Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
        putExtra(
            RecognizerIntent.EXTRA_LANGUAGE_MODEL,
            RecognizerIntent.LANGUAGE_MODEL_FREE_FORM,
        )
        putExtra(RecognizerIntent.EXTRA_LANGUAGE, languageTag)
        putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, true)
        putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 1)
    }

internal fun Int.toSpeechRecognitionFailure(): SpeechRecognitionFailure = when (this) {
    SpeechRecognizer.ERROR_NETWORK_TIMEOUT,
    SpeechRecognizer.ERROR_NETWORK,
    -> SpeechRecognitionFailure.NETWORK
    SpeechRecognizer.ERROR_AUDIO -> SpeechRecognitionFailure.AUDIO
    SpeechRecognizer.ERROR_SERVER,
    SpeechRecognizer.ERROR_TOO_MANY_REQUESTS,
    SpeechRecognizer.ERROR_SERVER_DISCONNECTED,
    SpeechRecognizer.ERROR_CANNOT_CHECK_SUPPORT,
    SpeechRecognizer.ERROR_CANNOT_LISTEN_TO_DOWNLOAD_EVENTS,
    -> SpeechRecognitionFailure.SERVICE
    SpeechRecognizer.ERROR_CLIENT -> SpeechRecognitionFailure.CLIENT
    SpeechRecognizer.ERROR_SPEECH_TIMEOUT -> SpeechRecognitionFailure.NO_SPEECH
    SpeechRecognizer.ERROR_NO_MATCH -> SpeechRecognitionFailure.NO_MATCH
    SpeechRecognizer.ERROR_RECOGNIZER_BUSY -> SpeechRecognitionFailure.BUSY
    SpeechRecognizer.ERROR_INSUFFICIENT_PERMISSIONS ->
        SpeechRecognitionFailure.PERMISSION_DENIED
    SpeechRecognizer.ERROR_LANGUAGE_NOT_SUPPORTED,
    SpeechRecognizer.ERROR_LANGUAGE_UNAVAILABLE,
    -> SpeechRecognitionFailure.LANGUAGE_UNAVAILABLE
    else -> SpeechRecognitionFailure.SERVICE
}

private fun Bundle?.firstTranscript(): String? = this
    ?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)
    ?.firstOrNull()
    ?.takeIf(String::isNotBlank)

private fun runOnAndroidMainThread(operation: () -> Unit) {
    Handler(Looper.getMainLooper()).post(operation)
}
