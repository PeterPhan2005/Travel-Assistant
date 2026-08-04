package com.kltn.travelassistant.feature.itinerary.data

import kotlinx.serialization.SerializationException
import kotlinx.serialization.builtins.ListSerializer
import kotlinx.serialization.builtins.serializer
import kotlinx.serialization.json.Json

internal class InvalidSavedItineraryException : Exception()

internal class SavedItineraryLocalCodec(
    private val json: Json = strictSavedItineraryJson(),
) {
    fun encodeTextList(values: List<String>): String = try {
        json.encodeToString(ListSerializer(String.serializer()), values)
    } catch (exception: SerializationException) {
        throw InvalidSavedItineraryException()
    }

    fun decodeTextList(raw: String): List<String> = try {
        json.decodeFromString(ListSerializer(String.serializer()), raw)
    } catch (exception: SerializationException) {
        throw InvalidSavedItineraryException()
    } catch (exception: IllegalArgumentException) {
        throw InvalidSavedItineraryException()
    }
}

internal fun strictSavedItineraryJson(): Json = Json {
    ignoreUnknownKeys = false
    isLenient = false
    allowSpecialFloatingPointValues = false
    explicitNulls = true
    encodeDefaults = true
}
