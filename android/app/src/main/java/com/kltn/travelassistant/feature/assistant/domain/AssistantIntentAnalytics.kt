package com.kltn.travelassistant.feature.assistant.domain

enum class AssistantIntentOutcome {
    SUCCESS,
    PARTIAL,
    FAILED,
}

enum class AssistantIntentInputMode {
    MANUAL,
    VOICE,
}

interface AssistantIntentAnalytics {
    fun record(
        intent: AssistantIntent,
        outcome: AssistantIntentOutcome,
        inputMode: AssistantIntentInputMode,
    )
}
