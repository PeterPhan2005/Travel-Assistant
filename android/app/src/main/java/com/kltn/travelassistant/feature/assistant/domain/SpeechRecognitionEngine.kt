package com.kltn.travelassistant.feature.assistant.domain

fun interface SpeechRecognitionListener {
    fun onEvent(event: SpeechRecognitionEvent)
}

sealed interface SpeechRecognitionStartResult {
    data object Started : SpeechRecognitionStartResult

    data class Failure(
        val reason: SpeechRecognitionFailure,
    ) : SpeechRecognitionStartResult
}

interface SpeechRecognitionEngine : AutoCloseable {
    fun isAvailable(): Boolean

    fun start(
        languageTag: String,
        listener: SpeechRecognitionListener,
    ): SpeechRecognitionStartResult

    fun cancel()

    override fun close()
}
