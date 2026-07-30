package com.kltn.travelassistant.feature.assistant.domain

const val MAX_ASSISTANT_QUERY_CODE_POINTS = 1_000

fun boundAssistantQueryText(text: String): String {
    if (text.codePointCount(0, text.length) <= MAX_ASSISTANT_QUERY_CODE_POINTS) {
        return text
    }
    val endIndex = text.offsetByCodePoints(0, MAX_ASSISTANT_QUERY_CODE_POINTS)
    return text.substring(0, endIndex)
}

fun normalizeRecognizedAssistantQuery(text: String): String =
    boundAssistantQueryText(text.trim())

fun normalizeConfirmedAssistantQuery(text: String): String =
    boundAssistantQueryText(text.trim())
