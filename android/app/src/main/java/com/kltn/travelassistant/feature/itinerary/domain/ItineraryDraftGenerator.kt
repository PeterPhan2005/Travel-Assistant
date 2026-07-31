package com.kltn.travelassistant.feature.itinerary.domain

internal interface ItineraryDraftGenerator {
    suspend fun generate(
        request: ItineraryDraftRequest,
    ): ItineraryDraftGenerationResult
}

internal sealed interface ItineraryDraftGenerationResult {
    data class Success(
        val draft: ItineraryDraft,
    ) : ItineraryDraftGenerationResult

    data class Failure(
        val reason: ItineraryDraftFailure,
    ) : ItineraryDraftGenerationResult
}

internal enum class ItineraryDraftFailure(
    val retryable: Boolean,
) {
    OFFLINE(true),
    AUTHENTICATION_REQUIRED(true),
    INVALID_REQUEST(false),
    TIMEOUT(true),
    RATE_LIMITED(true),
    UNAVAILABLE(true),
    INVALID_RESPONSE(false),
    UNSUPPORTED_TRANSPORT(false),
}
