package com.kltn.travelassistant.data.preferences

import com.kltn.travelassistant.feature.preferences.domain.PreferenceDocument
import com.kltn.travelassistant.feature.preferences.domain.BudgetPreference
import com.kltn.travelassistant.feature.preferences.domain.TravelInterest
import com.kltn.travelassistant.feature.preferences.domain.TravelPace
import com.kltn.travelassistant.feature.preferences.domain.TravelPreferenceProfile
import com.kltn.travelassistant.feature.preferences.domain.toTravelPreferenceProfileOrNull
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonNull
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.jsonObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class PreferenceDocumentCodecTest {
    private val codec = PreferenceDocumentCodec()

    @Test
    fun strictEnvelopePreservesUnicodeAndNormalizesKeys() {
        val decoded = codec.decodeResponse(
            """{"schema_version":1,"preferences":{"z":true,"địa_điểm":"Thành phố Hồ Chí Minh"},"updated_at":"2026-07-28T01:02:03+00:00"}""",
        )

        assertEquals(listOf("z", "địa_điểm"), decoded.document.preferences.keys.toList())
        assertEquals(
            JsonPrimitive("Thành phố Hồ Chí Minh"),
            decoded.document.preferences["địa_điểm"],
        )
        assertEquals("2026-07-28T01:02:03Z", decoded.updatedAt)
    }

    @Test
    fun unknownEnvelopeFieldsAndUnsupportedVersionAreRejected() {
        listOf(
            """{"schema_version":1,"preferences":{},"updated_at":null,"unknown":true}""",
            """{"schema_version":3,"preferences":{},"updated_at":null}""",
            """{"schema_version":1,"preferences":[],"updated_at":null}""",
        ).forEach { raw ->
            expectInvalid {
                codec.decodeResponse(raw)
            }
        }
    }

    @Test
    fun recursiveBoundsRejectDecimalsDepthAndOversizedCollections() {
        val tooManyItems = JsonArray(List(MAX_PREFERENCE_ARRAY_ITEMS + 1) { JsonNull })
        val tooManyKeys = JsonObject(
            (0..MAX_PREFERENCE_OBJECT_ITEMS).associate { "k$it" to JsonNull },
        )
        var nested: JsonObject = JsonObject(emptyMap())
        repeat(MAX_PREFERENCE_CONTAINER_DEPTH + 2) {
            nested = JsonObject(mapOf("next" to nested))
        }
        val invalidDocuments = listOf(
            PreferenceDocument(preferences = JsonObject(mapOf("decimal" to JsonPrimitive(1.5)))),
            PreferenceDocument(preferences = JsonObject(mapOf("array" to tooManyItems))),
            PreferenceDocument(preferences = tooManyKeys),
            PreferenceDocument(preferences = nested),
            PreferenceDocument(
                preferences = JsonObject(
                    mapOf("text" to JsonPrimitive("x".repeat(MAX_PREFERENCE_STRING_LENGTH + 1))),
                ),
            ),
        )

        invalidDocuments.forEach { document ->
            expectInvalid {
                codec.validate(document)
            }
        }
    }

    @Test
    fun requestContainsOnlyStrictCompleteEnvelope() {
        val encoded = codec.encodeRequest(
            PreferenceDocument(
                preferences = JsonObject(
                    mapOf(
                        "neutral_test_key" to JsonArray(
                            listOf(JsonPrimitive(1), JsonPrimitive(false), JsonNull),
                        ),
                    ),
                ),
            ),
        )

        assertTrue(encoded.startsWith("""{"schema_version":1,"preferences":{"""))
        assertEquals(
            setOf("schema_version", "preferences"),
            strictPreferenceJson().parseToJsonElement(encoded).jsonObject.keys,
        )
    }

    @Test
    fun typedTravelDocumentRoundTripsInCanonicalOrder() {
        val profile = TravelPreferenceProfile(
            interests = setOf(
                TravelInterest.NATURE_AND_OUTDOORS,
                TravelInterest.FOOD_AND_CAFES,
            ),
            pace = TravelPace.BALANCED,
            budgetPreference = BudgetPreference.MODERATE,
        )

        val encoded = codec.encodeRequest(profile.toDocument())
        val decoded = codec.decodeResponse(
            encoded.dropLast(1) + ",\"updated_at\":null}",
        )

        assertEquals(2, decoded.document.schemaVersion)
        assertEquals(profile, decoded.document.toTravelPreferenceProfileOrNull())
        assertTrue(
            encoded.indexOf("food_and_cafes") < encoded.indexOf("nature_and_outdoors"),
        )
    }

    @Test
    fun typedTravelDocumentRejectsPartialUnknownDuplicateAndTooManyInterests() {
        listOf(
            """{"schema_version":2,"preferences":{"interests":[],"pace":null},"updated_at":null}""",
            """{"schema_version":2,"preferences":{"interests":[],"pace":null,"budget_preference":null,"hidden":true},"updated_at":null}""",
            """{"schema_version":2,"preferences":{"interests":["food_and_cafes","food_and_cafes"],"pace":null,"budget_preference":null},"updated_at":null}""",
            """{"schema_version":2,"preferences":{"interests":["food_and_cafes","culture_and_history","scenic_and_landmarks","nature_and_outdoors","local_life_and_markets","family_activities"],"pace":null,"budget_preference":null},"updated_at":null}""",
        ).forEach { raw -> expectInvalid { codec.decodeResponse(raw) } }
    }

    private fun expectInvalid(block: () -> Unit) {
        try {
            block()
            throw AssertionError("Expected InvalidPreferenceDocumentException")
        } catch (exception: InvalidPreferenceDocumentException) {
            assertTrue(true)
        }
    }
}
