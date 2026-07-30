package com.kltn.travelassistant.feature.assistant.domain

sealed interface SpeechRecognitionEvent {
    data object Ready : SpeechRecognitionEvent

    data object Listening : SpeechRecognitionEvent

    data class PartialTranscript(val text: String) : SpeechRecognitionEvent

    data class FinalTranscript(val text: String) : SpeechRecognitionEvent

    data object EndOfSpeech : SpeechRecognitionEvent

    data object Cancelled : SpeechRecognitionEvent

    data class Failure(
        val reason: SpeechRecognitionFailure,
    ) : SpeechRecognitionEvent
}
