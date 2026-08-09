package com.kltn.travelassistant.analytics

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertThrows
import org.junit.Assert.assertTrue
import org.junit.Test

class ProductAnalyticsSchemaTest {
    @Test
    fun versionOneHasExactlyFiveClosedEventNamesAndSixPropertyKeys() {
        assertEquals(1, PRODUCT_ANALYTICS_SCHEMA_VERSION)
        assertEquals(
            listOf(
                "navigation_conversion",
                "itinerary_creation",
                "voice_intent_result",
                "trip_return",
                "geocontext_opened",
            ),
            ProductAnalyticsEventName.entries.map(ProductAnalyticsEventName::wireValue),
        )
        assertEquals(
            listOf(
                "stage",
                "poi_id",
                "outcome",
                "failure_category",
                "intent",
                "result_state",
            ),
            ProductAnalyticsPropertyKey.entries.map(ProductAnalyticsPropertyKey::wireValue),
        )
    }

    @Test
    fun everyEventEncodesOnlyItsExactApprovedProperties() {
        val cases = listOf(
            ProductAnalyticsEvent.NavigationConversion(
                NavigationConversionStage.DETAIL_OPENED,
                "hcmc-ben-thanh-market",
            ) to listOf("stage=detail_opened", "poi_id=hcmc-ben-thanh-market"),
            ProductAnalyticsEvent.ItineraryCreation(
                outcome = ItineraryCreationOutcome.FAILED,
                failureCategory = ItineraryFailureCategory.TIMEOUT,
            ) to listOf("outcome=failed", "failure_category=timeout"),
            ProductAnalyticsEvent.VoiceIntentResult(
                AnalyticsAssistantIntent.NEARBY_DISCOVERY,
                VoiceIntentOutcome.PARTIAL,
            ) to listOf("intent=nearby_discovery", "outcome=partial"),
            ProductAnalyticsEvent.TripReturn to emptyList(),
            ProductAnalyticsEvent.GeocontextOpened(
                GeocontextResultState.CONTENT,
            ) to listOf("result_state=content"),
        )

        cases.forEach { (event, expected) ->
            assertEquals(
                expected,
                ProductAnalyticsSchema.properties(event).map { property ->
                    "${property.key.wireValue}=${property.value}"
                },
            )
        }
    }

    @Test
    fun propertyValueDomainsAreClosedAndFailureClosureIsEnforced() {
        assertEquals(
            listOf("detail_opened", "navigation_requested"),
            NavigationConversionStage.entries.map(NavigationConversionStage::wireValue),
        )
        assertEquals(
            listOf("attempted", "succeeded", "cancelled", "failed"),
            ItineraryCreationOutcome.entries.map(ItineraryCreationOutcome::wireValue),
        )
        assertEquals(
            listOf("success", "partial", "failed"),
            VoiceIntentOutcome.entries.map(VoiceIntentOutcome::wireValue),
        )
        assertThrows(IllegalArgumentException::class.java) {
            ProductAnalyticsEvent.ItineraryCreation(
                outcome = ItineraryCreationOutcome.FAILED,
            )
        }
        assertThrows(IllegalArgumentException::class.java) {
            ProductAnalyticsEvent.ItineraryCreation(
                outcome = ItineraryCreationOutcome.SUCCEEDED,
                failureCategory = ItineraryFailureCategory.INVALID_RESPONSE,
            )
        }
    }

    @Test
    fun schemaCannotNameProhibitedSensitiveProperties() {
        val keys = ProductAnalyticsPropertyKey.entries
            .map(ProductAnalyticsPropertyKey::wireValue)
            .joinToString(" ")
            .lowercase()
        listOf(
            "query",
            "transcript",
            "prompt",
            "response",
            "latitude",
            "longitude",
            "coordinate",
            "address",
            "uid",
            "email",
            "account",
            "token",
            "authorization",
            "exception",
            "stack",
            "device_id",
            "advertising",
        ).forEach { prohibited ->
            assertFalse(keys.contains(prohibited))
        }
        assertTrue(ProductAnalyticsEventName.entries.all { it.wireValue.length <= 40 })
    }
}
