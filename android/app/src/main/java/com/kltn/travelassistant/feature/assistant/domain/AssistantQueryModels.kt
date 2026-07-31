package com.kltn.travelassistant.feature.assistant.domain

const val MAX_ASSISTANT_SUBMISSION_CODE_POINTS = 500

data class AssistantLocationSnapshot(
    val latitude: Double,
    val longitude: Double,
) {
    init {
        require(latitude.isFinite() && latitude in -90.0..90.0)
        require(longitude.isFinite() && longitude in -180.0..180.0)
    }
}

data class AssistantQueryRequest(
    val text: String,
    val location: AssistantLocationSnapshot?,
)

enum class AssistantIntent {
    NEARBY_DISCOVERY,
    POI_INFORMATION,
    LOCAL_CULTURE,
    ITINERARY_DRAFTING,
    GENERAL_TRAVEL_HELP,
    UNSUPPORTED,
}

enum class AssistantResultStatus {
    SUCCESS,
    PARTIAL,
    FAILED,
}

data class AssistantPrice(
    val minorUnits: Long,
    val currency: String,
    val updatedAt: String,
)

data class AssistantPoiResult(
    val name: String,
    val category: String,
    val address: String?,
    val distanceMetres: Double?,
    val rating: Double?,
    val ratingCount: Int?,
    val price: AssistantPrice?,
    val openingHoursSummary: String?,
)

data class AssistantSource(
    val label: String,
    val publisher: String?,
    val url: String?,
)

data class AssistantWarning(
    val message: String,
    val retryable: Boolean,
)

data class AssistantNarration(
    val text: String,
    val keyPoints: List<String>,
)

data class AssistantItineraryItem(
    val title: String,
    val startLocalTime: String,
    val endLocalTime: String,
)

data class AssistantItinerary(
    val localDate: String,
    val timezone: String,
    val items: List<AssistantItineraryItem>,
    val assumptions: List<String>,
)

data class AssistantQueryResult(
    val status: AssistantResultStatus,
    val intent: AssistantIntent?,
    val message: String,
    val poiResults: List<AssistantPoiResult>,
    val narration: AssistantNarration?,
    val itinerary: AssistantItinerary?,
    val sources: List<AssistantSource>,
    val warnings: List<AssistantWarning>,
    val retryable: Boolean,
)

enum class AssistantQueryFailure {
    OFFLINE,
    AUTHENTICATION_REQUIRED,
    CONFIGURATION,
    INVALID_REQUEST,
    TIMEOUT,
    RATE_LIMITED,
    UNAVAILABLE,
    INVALID_RESPONSE,
}

sealed interface AssistantRepositoryResult {
    data class Structured(
        val result: AssistantQueryResult,
    ) : AssistantRepositoryResult

    data class Failure(
        val reason: AssistantQueryFailure,
    ) : AssistantRepositoryResult
}
