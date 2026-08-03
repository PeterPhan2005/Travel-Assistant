package com.kltn.travelassistant.feature.itinerary.data

import com.kltn.travelassistant.feature.itinerary.domain.ItineraryCity
import com.kltn.travelassistant.feature.itinerary.domain.ItineraryDraft
import com.kltn.travelassistant.feature.itinerary.domain.ItineraryDraftFailure
import com.kltn.travelassistant.feature.itinerary.domain.ItineraryDraftGenerationResult
import com.kltn.travelassistant.feature.itinerary.domain.ItineraryDraftItem
import com.kltn.travelassistant.feature.itinerary.domain.ItineraryDraftRequest
import com.kltn.travelassistant.feature.itinerary.domain.ItineraryDraftWarning
import com.kltn.travelassistant.feature.itinerary.domain.MAX_ITINERARY_NOTES_CODE_POINTS
import java.time.LocalDate
import java.time.LocalTime
import java.time.format.DateTimeFormatter
import java.time.format.DateTimeParseException
import javax.inject.Inject
import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import kotlinx.serialization.SerializationException
import kotlinx.serialization.json.Json

internal class InvalidItineraryJsonException : Exception()

internal class ItineraryJsonCodec @Inject constructor() {
    private val json = Json {
        ignoreUnknownKeys = false
        isLenient = false
        explicitNulls = true
        encodeDefaults = true
        coerceInputValues = false
    }

    fun encodeRequest(request: ItineraryDraftRequest): String {
        validateRequest(request)
        val document = ItineraryRequestDocument(
            city = request.city.transportValue,
            localDate = request.localDate.toString(),
            timezone = request.timezone,
            startLocalTime = request.startLocalTime.format(REQUEST_TIME_FORMAT),
            endLocalTime = request.endLocalTime.format(REQUEST_TIME_FORMAT),
            maximumStops = request.maximumStops,
            notes = request.notes,
            locale = VIETNAMESE_LOCALE,
            clientMode = ONLINE_MODE,
            latitude = request.currentLocation?.latitude,
            longitude = request.currentLocation?.longitude,
        )
        return try {
            json.encodeToString(ItineraryRequestDocument.serializer(), document)
        } catch (_: SerializationException) {
            throw InvalidItineraryJsonException()
        }
    }

    fun decodeResponse(body: String): ItineraryDraftGenerationResult {
        val document = try {
            json.decodeFromString(ItineraryResponseDocument.serializer(), body)
        } catch (_: SerializationException) {
            throw InvalidItineraryJsonException()
        }
        return try {
            document.toDomain()
        } catch (_: IllegalArgumentException) {
            throw InvalidItineraryJsonException()
        }
    }

    private fun validateRequest(request: ItineraryDraftRequest) {
        val notes = request.notes
        val validNotes = notes == null || (
            notes.isNotBlank() &&
                notes.codePointCount(0, notes.length) <= MAX_ITINERARY_NOTES_CODE_POINTS &&
                notes.none(Char::isISOControl)
            )
        if (
            request.timezone != request.city.timezone ||
            request.startLocalTime >= request.endLocalTime ||
            request.maximumStops !in 1..20 ||
            !validNotes
        ) {
            throw InvalidItineraryJsonException()
        }
    }

    private companion object {
        const val VIETNAMESE_LOCALE = "vi-VN"
        const val ONLINE_MODE = "online"
        val REQUEST_TIME_FORMAT: DateTimeFormatter = DateTimeFormatter.ofPattern("HH:mm")
    }
}

@Serializable
private data class ItineraryRequestDocument(
    val city: String,
    @SerialName("local_date") val localDate: String,
    val timezone: String,
    @SerialName("start_local_time") val startLocalTime: String,
    @SerialName("end_local_time") val endLocalTime: String,
    @SerialName("maximum_stops") val maximumStops: Int,
    val notes: String?,
    val locale: String,
    @SerialName("client_mode") val clientMode: String,
    val latitude: Double?,
    val longitude: Double?,
)

@Serializable
private data class ItineraryResponseDocument(
    val status: String,
    val city: String,
    @SerialName("local_date") val localDate: String,
    val timezone: String,
    @SerialName("start_local_time") val startLocalTime: String,
    @SerialName("end_local_time") val endLocalTime: String,
    val items: List<ItineraryItemDocument>,
    val assumptions: List<String>,
    val warnings: List<String>,
    @SerialName("failure_category") val failureCategory: String?,
    val retryable: Boolean,
) {
    fun toDomain(): ItineraryDraftGenerationResult {
        require(items.size <= 20 && assumptions.size <= 10 && warnings.size <= 30)
        val parsedCity = city.toItineraryCity()
        val date = LocalDate.parse(localDate)
        val start = parseBackendMinuteTime(startLocalTime)
        val end = parseBackendMinuteTime(endLocalTime)
        require(timezone == parsedCity.timezone && start < end)
        if (status == "failed") {
            require(items.isEmpty() && assumptions.isEmpty())
            val category = requireNotNull(failureCategory)
            require(category in FAILURE_CATEGORIES)
            return ItineraryDraftGenerationResult.Failure(
                if (retryable) {
                    ItineraryDraftFailure.UNAVAILABLE
                } else {
                    ItineraryDraftFailure.INVALID_RESPONSE
                },
            )
        }
        require(status == "success" || status == "partial")
        require(failureCategory == null && items.isNotEmpty() && assumptions.isNotEmpty())
        require(assumptions.all { it.isSafeText() } && warnings.all { it.isSafeText() })
        require(status != "success" || warnings.isEmpty() && !retryable)
        require(status != "partial" || warnings.isNotEmpty())
        return ItineraryDraftGenerationResult.Success(
            ItineraryDraft(
                city = parsedCity,
                localDate = date,
                timezone = timezone,
                startLocalTime = start,
                endLocalTime = end,
                items = items.map(ItineraryItemDocument::toDomain),
                assumptions = assumptions,
                warnings = warnings.map(::ItineraryDraftWarning),
            ),
        )
    }
}

@Serializable
private data class ItineraryItemDocument(
    @SerialName("start_local_time") val startLocalTime: String,
    @SerialName("end_local_time") val endLocalTime: String,
    val title: String,
) {
    fun toDomain(): ItineraryDraftItem {
        val start = parseBackendMinuteTime(startLocalTime)
        val end = parseBackendMinuteTime(endLocalTime)
        require(start < end && title.isSafeText())
        return ItineraryDraftItem(title, start, end)
    }
}

private val ItineraryCity.transportValue: String
    get() = when (this) {
        ItineraryCity.HO_CHI_MINH_CITY -> "hcmc"
        ItineraryCity.BANGKOK -> "bkk"
    }

private fun String.toItineraryCity(): ItineraryCity = when (this) {
    "hcmc" -> ItineraryCity.HO_CHI_MINH_CITY
    "bkk" -> ItineraryCity.BANGKOK
    else -> throw IllegalArgumentException()
}

private fun parseBackendMinuteTime(value: String): LocalTime {
    require(BACKEND_MINUTE_TIME_PATTERN.matches(value))
    return try {
        LocalTime.parse(value)
    } catch (_: DateTimeParseException) {
        throw IllegalArgumentException()
    }
}

private fun String.isSafeText(): Boolean =
    isNotBlank() && length <= 240 && none(Char::isISOControl)

private val BACKEND_MINUTE_TIME_PATTERN = Regex("^[0-9]{2}:[0-9]{2}:00$")
private val FAILURE_CATEGORIES = setOf(
    "insufficient_candidates",
    "candidate_resolution_unavailable",
    "generation_unavailable",
    "invalid_generation_output",
)
