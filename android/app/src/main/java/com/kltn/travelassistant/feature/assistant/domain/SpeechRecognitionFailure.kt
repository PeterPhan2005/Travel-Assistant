package com.kltn.travelassistant.feature.assistant.domain

enum class SpeechRecognitionFailure {
    SERVICE_UNAVAILABLE,
    PERMISSION_DENIED,
    NO_SPEECH,
    NO_MATCH,
    NETWORK,
    AUDIO,
    BUSY,
    LANGUAGE_UNAVAILABLE,
    SERVICE,
    CLIENT,
}
