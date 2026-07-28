package com.kltn.travelassistant.data.preferences

import com.kltn.travelassistant.feature.preferences.domain.PREFERENCE_SCHEMA_VERSION
import com.kltn.travelassistant.feature.preferences.domain.PreferenceDocument
import java.time.DateTimeException
import java.time.Instant
import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import kotlinx.serialization.SerializationException
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.JsonNull
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive

internal const val MAX_PREFERENCE_DOCUMENT_BYTES = 16_384
internal const val MAX_PREFERENCE_CONTAINER_DEPTH = 6
internal const val MAX_PREFERENCE_KEY_LENGTH = 64
internal const val MAX_PREFERENCE_STRING_LENGTH = 512
internal const val MAX_PREFERENCE_ARRAY_ITEMS = 50
internal const val MAX_PREFERENCE_OBJECT_ITEMS = 50
internal const val MAX_PREFERENCE_TOTAL_VALUES = 500
internal const val MAX_PREFERENCE_INTEGER_ABSOLUTE_VALUE = 1_000_000_000_000L

internal class InvalidPreferenceDocumentException : Exception()

@Serializable
private data class PreferenceRequestWire(
    @SerialName("schema_version")
    val schemaVersion: Int,
    val preferences: JsonObject,
)

@Serializable
private data class PreferenceResponseWire(
    @SerialName("schema_version")
    val schemaVersion: Int,
    val preferences: JsonObject,
    @SerialName("updated_at")
    val updatedAt: String?,
)

internal data class ServerPreferenceDocument(
    val document: PreferenceDocument,
    val updatedAt: String?,
)

internal class PreferenceDocumentCodec(
    private val json: Json = strictPreferenceJson(),
) {
    fun validate(document: PreferenceDocument): PreferenceDocument {
        if (document.schemaVersion != PREFERENCE_SCHEMA_VERSION) {
            throw InvalidPreferenceDocumentException()
        }
        val counter = ValueCounter()
        val normalized = validateObject(document.preferences, depth = 0, counter = counter)
        val normalizedDocument = PreferenceDocument(
            schemaVersion = PREFERENCE_SCHEMA_VERSION,
            preferences = normalized,
        )
        val bytes = json.encodeToString(
            PreferenceRequestWire.serializer(),
            PreferenceRequestWire(
                schemaVersion = normalizedDocument.schemaVersion,
                preferences = normalizedDocument.preferences,
            ),
        ).toByteArray(Charsets.UTF_8)
        if (bytes.size > MAX_PREFERENCE_DOCUMENT_BYTES) {
            throw InvalidPreferenceDocumentException()
        }
        return normalizedDocument
    }

    fun encodeRequest(document: PreferenceDocument): String {
        val normalized = validate(document)
        return json.encodeToString(
            PreferenceRequestWire.serializer(),
            PreferenceRequestWire(
                schemaVersion = normalized.schemaVersion,
                preferences = normalized.preferences,
            ),
        )
    }

    fun decodeResponse(raw: String): ServerPreferenceDocument {
        val wire = try {
            json.decodeFromString(PreferenceResponseWire.serializer(), raw)
        } catch (exception: SerializationException) {
            throw InvalidPreferenceDocumentException()
        } catch (exception: IllegalArgumentException) {
            throw InvalidPreferenceDocumentException()
        }
        val document = validate(
            PreferenceDocument(
                schemaVersion = wire.schemaVersion,
                preferences = wire.preferences,
            ),
        )
        val updatedAt = wire.updatedAt?.let(::normalizeServerTimestamp)
        return ServerPreferenceDocument(document, updatedAt)
    }

    fun normalizeServerTimestamp(value: String): String = try {
        Instant.parse(value).toString()
    } catch (exception: DateTimeException) {
        throw InvalidPreferenceDocumentException()
    }

    private fun validateObject(
        value: JsonObject,
        depth: Int,
        counter: ValueCounter,
    ): JsonObject {
        validateDepth(depth)
        if (value.size > MAX_PREFERENCE_OBJECT_ITEMS) {
            throw InvalidPreferenceDocumentException()
        }
        return JsonObject(
            value.toSortedMap().mapValues { (key, item) ->
                if (key.isEmpty() || key.length > MAX_PREFERENCE_KEY_LENGTH) {
                    throw InvalidPreferenceDocumentException()
                }
                counter.add()
                validateValue(item, depth + 1, counter)
            },
        )
    }

    private fun validateArray(
        value: JsonArray,
        depth: Int,
        counter: ValueCounter,
    ): JsonArray {
        validateDepth(depth)
        if (value.size > MAX_PREFERENCE_ARRAY_ITEMS) {
            throw InvalidPreferenceDocumentException()
        }
        return JsonArray(
            value.map { item ->
                counter.add()
                validateValue(item, depth + 1, counter)
            },
        )
    }

    private fun validateValue(
        value: JsonElement,
        depth: Int,
        counter: ValueCounter,
    ): JsonElement = when (value) {
        JsonNull -> JsonNull
        is JsonObject -> validateObject(value, depth, counter)
        is JsonArray -> validateArray(value, depth, counter)
        is JsonPrimitive -> validatePrimitive(value)
    }

    private fun validatePrimitive(value: JsonPrimitive): JsonPrimitive {
        if (value.isString) {
            if (value.content.length > MAX_PREFERENCE_STRING_LENGTH) {
                throw InvalidPreferenceDocumentException()
            }
            return value
        }
        if (value.content == "true" || value.content == "false") return value
        if (!INTEGER_PATTERN.matches(value.content)) {
            throw InvalidPreferenceDocumentException()
        }
        val number = value.content.toLongOrNull()
            ?: throw InvalidPreferenceDocumentException()
        if (
            number < -MAX_PREFERENCE_INTEGER_ABSOLUTE_VALUE ||
            number > MAX_PREFERENCE_INTEGER_ABSOLUTE_VALUE
        ) {
            throw InvalidPreferenceDocumentException()
        }
        return JsonPrimitive(number)
    }

    private fun validateDepth(depth: Int) {
        if (depth > MAX_PREFERENCE_CONTAINER_DEPTH) {
            throw InvalidPreferenceDocumentException()
        }
    }

    private class ValueCounter {
        private var value = 0

        fun add() {
            value += 1
            if (value > MAX_PREFERENCE_TOTAL_VALUES) {
                throw InvalidPreferenceDocumentException()
            }
        }
    }

    private companion object {
        val INTEGER_PATTERN = Regex("^-?(0|[1-9][0-9]*)$")
    }
}

internal fun strictPreferenceJson(): Json = Json {
    ignoreUnknownKeys = false
    isLenient = false
    allowSpecialFloatingPointValues = false
    explicitNulls = true
    encodeDefaults = true
}
