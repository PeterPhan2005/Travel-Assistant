package com.kltn.travelassistant.feature.assistant.data

import com.kltn.travelassistant.feature.assistant.domain.AssistantIntent
import com.kltn.travelassistant.feature.assistant.domain.AssistantItinerary
import com.kltn.travelassistant.feature.assistant.domain.AssistantItineraryItem
import com.kltn.travelassistant.feature.assistant.domain.AssistantLocationSnapshot
import com.kltn.travelassistant.feature.assistant.domain.AssistantNarration
import com.kltn.travelassistant.feature.assistant.domain.AssistantPoiResult
import com.kltn.travelassistant.feature.assistant.domain.AssistantPrice
import com.kltn.travelassistant.feature.assistant.domain.AssistantQueryRequest
import com.kltn.travelassistant.feature.assistant.domain.AssistantQueryResult
import com.kltn.travelassistant.feature.assistant.domain.AssistantResultStatus
import com.kltn.travelassistant.feature.assistant.domain.AssistantSource
import com.kltn.travelassistant.feature.assistant.domain.AssistantWarning
import java.time.LocalDate
import java.time.LocalTime
import java.time.OffsetDateTime
import javax.inject.Inject
import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import kotlinx.serialization.SerializationException
import kotlinx.serialization.json.Json

internal class InvalidAssistantJsonException : Exception()

internal class AssistantJsonCodec @Inject constructor() {
    private val json = Json {
        ignoreUnknownKeys = false
        isLenient = false
        explicitNulls = true
        encodeDefaults = true
        coerceInputValues = false
    }

    fun encodeRequest(request: AssistantQueryRequest): String {
        val document = AssistantRequestDocument(
            text = request.text,
            locale = VIETNAMESE_LOCALE,
            latitude = request.location?.latitude,
            longitude = request.location?.longitude,
            tripId = null,
            clientMode = ONLINE_MODE,
        )
        return try {
            json.encodeToString(AssistantRequestDocument.serializer(), document)
        } catch (_: SerializationException) {
            throw InvalidAssistantJsonException()
        }
    }

    fun decodeResponse(body: String): AssistantQueryResult {
        val document = try {
            json.decodeFromString(AssistantResponseDocument.serializer(), body)
        } catch (_: SerializationException) {
            throw InvalidAssistantJsonException()
        }
        return try {
            document.toDomain()
        } catch (_: IllegalArgumentException) {
            throw InvalidAssistantJsonException()
        }
    }

    private companion object {
        const val VIETNAMESE_LOCALE = "vi-VN"
        const val ONLINE_MODE = "online"
    }
}

@Serializable
private data class AssistantRequestDocument(
    val text: String,
    val locale: String,
    val latitude: Double?,
    val longitude: Double?,
    @SerialName("trip_id")
    val tripId: String?,
    @SerialName("client_mode")
    val clientMode: String,
)

@Serializable
private data class AssistantResponseDocument(
    @SerialName("request_id")
    val requestId: String,
    val status: String,
    val intent: String?,
    val message: String,
    @SerialName("poi_results")
    val poiResults: List<AssistantPoiDocument>,
    val narration: AssistantNarrationDocument?,
    val itinerary: AssistantItineraryDocument?,
    val sources: List<AssistantSourceDocument>,
    val warnings: List<AssistantWarningDocument>,
    val retryable: Boolean,
) {
    fun toDomain(): AssistantQueryResult {
        require(requestId.isNotBlank() && requestId.length <= 128)
        require(message.isNotBlank() && message.length <= 6_000)
        require(poiResults.size <= 20)
        require(sources.size <= 100)
        require(warnings.size <= 30)
        return AssistantQueryResult(
            status = status.toStatus(),
            intent = intent?.toIntent(),
            message = message,
            poiResults = poiResults.map(AssistantPoiDocument::toDomain),
            narration = narration?.toDomain(),
            itinerary = itinerary?.toDomain(),
            sources = sources.map(AssistantSourceDocument::toDomain),
            warnings = warnings.map(AssistantWarningDocument::toDomain),
            retryable = retryable,
        )
    }
}

@Serializable
private data class AssistantPoiDocument(
    val name: String,
    val category: String,
    val address: String?,
    @SerialName("distance_metres")
    val distanceMetres: Double?,
    val rating: Double?,
    @SerialName("rating_count")
    val ratingCount: Int?,
    val price: AssistantPriceDocument?,
    @SerialName("opening_hours_summary")
    val openingHoursSummary: String?,
) {
    fun toDomain(): AssistantPoiResult {
        require(name.isNotBlank() && name.length <= 200)
        require(category.isNotBlank() && category.length <= 200)
        require(address == null || address.isNotBlank())
        require(distanceMetres == null || distanceMetres.isFinite() && distanceMetres >= 0)
        require(rating == null || rating.isFinite() && rating in 0.0..5.0)
        require(ratingCount == null || ratingCount >= 0)
        require(openingHoursSummary == null || openingHoursSummary.isNotBlank())
        return AssistantPoiResult(
            name = name,
            category = category,
            address = address,
            distanceMetres = distanceMetres,
            rating = rating,
            ratingCount = ratingCount,
            price = price?.toDomain(),
            openingHoursSummary = openingHoursSummary,
        )
    }
}

@Serializable
private data class AssistantPriceDocument(
    @SerialName("minor_units")
    val minorUnits: Long,
    val currency: String,
    @SerialName("updated_at")
    val updatedAt: String,
) {
    fun toDomain(): AssistantPrice {
        require(minorUnits >= 0)
        require(currency.matches(Regex("^[A-Z]{3}$")))
        OffsetDateTime.parse(updatedAt)
        return AssistantPrice(minorUnits, currency, updatedAt)
    }
}

@Serializable
private data class AssistantSourceDocument(
    val label: String,
    val publisher: String?,
    val url: String?,
    @SerialName("published_at")
    val publishedAt: String?,
    @SerialName("retrieved_at")
    val retrievedAt: String?,
) {
    fun toDomain(): AssistantSource {
        require(label.isNotBlank() && label.length <= 200)
        require(publisher == null || publisher.isNotBlank())
        require(url == null || url.startsWith("https://"))
        publishedAt?.let(OffsetDateTime::parse)
        retrievedAt?.let(OffsetDateTime::parse)
        return AssistantSource(label, publisher, url)
    }
}

@Serializable
private data class AssistantWarningDocument(
    val message: String,
    val retryable: Boolean,
) {
    fun toDomain(): AssistantWarning {
        require(message.isNotBlank() && message.length <= 240)
        return AssistantWarning(message, retryable)
    }
}

@Serializable
private data class AssistantNarrationDocument(
    val text: String,
    @SerialName("key_points")
    val keyPoints: List<String>,
) {
    fun toDomain(): AssistantNarration {
        require(text.isNotBlank() && text.length <= 6_000)
        require(keyPoints.size <= 10 && keyPoints.all(String::isNotBlank))
        return AssistantNarration(text, keyPoints)
    }
}

@Serializable
private data class AssistantItineraryDocument(
    @SerialName("local_date")
    val localDate: String,
    val timezone: String,
    val items: List<AssistantItineraryItemDocument>,
    val assumptions: List<String>,
    @SerialName("draft_only")
    val draftOnly: Boolean,
) {
    fun toDomain(): AssistantItinerary {
        LocalDate.parse(localDate)
        require(timezone.isNotBlank() && timezone.length <= 64)
        require(items.isNotEmpty() && items.size <= 20)
        require(assumptions.size <= 10 && assumptions.all(String::isNotBlank))
        require(draftOnly)
        return AssistantItinerary(
            localDate = localDate,
            timezone = timezone,
            items = items.map(AssistantItineraryItemDocument::toDomain),
            assumptions = assumptions,
        )
    }
}

@Serializable
private data class AssistantItineraryItemDocument(
    val title: String,
    @SerialName("start_local_time")
    val startLocalTime: String,
    @SerialName("end_local_time")
    val endLocalTime: String,
) {
    fun toDomain(): AssistantItineraryItem {
        require(title.isNotBlank() && title.length <= 240)
        val start = LocalTime.parse(startLocalTime)
        val end = LocalTime.parse(endLocalTime)
        require(start < end)
        return AssistantItineraryItem(title, startLocalTime, endLocalTime)
    }
}

private fun String.toStatus(): AssistantResultStatus = when (this) {
    "success" -> AssistantResultStatus.SUCCESS
    "partial" -> AssistantResultStatus.PARTIAL
    "failed" -> AssistantResultStatus.FAILED
    else -> throw IllegalArgumentException()
}

private fun String.toIntent(): AssistantIntent = when (this) {
    "nearby_discovery" -> AssistantIntent.NEARBY_DISCOVERY
    "poi_information" -> AssistantIntent.POI_INFORMATION
    "local_culture" -> AssistantIntent.LOCAL_CULTURE
    "itinerary_drafting" -> AssistantIntent.ITINERARY_DRAFTING
    "general_travel_help" -> AssistantIntent.GENERAL_TRAVEL_HELP
    "unsupported" -> AssistantIntent.UNSUPPORTED
    else -> throw IllegalArgumentException()
}
