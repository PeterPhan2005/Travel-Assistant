package com.kltn.travelassistant.feature.assistant.data

import com.kltn.travelassistant.analytics.AnalyticsAssistantIntent
import com.kltn.travelassistant.analytics.ProductAnalytics
import com.kltn.travelassistant.analytics.ProductAnalyticsEvent
import com.kltn.travelassistant.analytics.VoiceIntentOutcome
import com.kltn.travelassistant.feature.assistant.domain.AssistantIntent
import com.kltn.travelassistant.feature.assistant.domain.AssistantIntentInputMode
import com.kltn.travelassistant.feature.assistant.domain.AssistantIntentOutcome
import org.junit.Assert.assertEquals
import org.junit.Test

class ProductAssistantIntentAnalyticsTest {
    @Test
    fun voiceIntentAndOutcomeMapExhaustivelyWithoutTranscriptOrEntity() {
        val productAnalytics = RecordingProductAnalytics()
        val analytics = ProductAssistantIntentAnalytics(productAnalytics)

        AssistantIntent.entries.forEachIndexed { index, intent ->
            analytics.record(
                intent = intent,
                outcome = AssistantIntentOutcome.entries[index % AssistantIntentOutcome.entries.size],
                inputMode = AssistantIntentInputMode.VOICE,
            )
        }

        assertEquals(
            listOf(
                ProductAnalyticsEvent.VoiceIntentResult(
                    AnalyticsAssistantIntent.NEARBY_DISCOVERY,
                    VoiceIntentOutcome.SUCCESS,
                ),
                ProductAnalyticsEvent.VoiceIntentResult(
                    AnalyticsAssistantIntent.POI_INFORMATION,
                    VoiceIntentOutcome.PARTIAL,
                ),
                ProductAnalyticsEvent.VoiceIntentResult(
                    AnalyticsAssistantIntent.LOCAL_CULTURE,
                    VoiceIntentOutcome.FAILED,
                ),
                ProductAnalyticsEvent.VoiceIntentResult(
                    AnalyticsAssistantIntent.ITINERARY_DRAFTING,
                    VoiceIntentOutcome.SUCCESS,
                ),
                ProductAnalyticsEvent.VoiceIntentResult(
                    AnalyticsAssistantIntent.GENERAL_TRAVEL_HELP,
                    VoiceIntentOutcome.PARTIAL,
                ),
                ProductAnalyticsEvent.VoiceIntentResult(
                    AnalyticsAssistantIntent.UNSUPPORTED,
                    VoiceIntentOutcome.FAILED,
                ),
            ),
            productAnalytics.events,
        )
    }

    @Test
    fun manualIntentResultProducesNoVoiceKpiEvent() {
        val productAnalytics = RecordingProductAnalytics()
        val analytics = ProductAssistantIntentAnalytics(productAnalytics)

        analytics.record(
            AssistantIntent.NEARBY_DISCOVERY,
            AssistantIntentOutcome.SUCCESS,
            AssistantIntentInputMode.MANUAL,
        )

        assertEquals(emptyList<ProductAnalyticsEvent>(), productAnalytics.events)
    }

    private class RecordingProductAnalytics : ProductAnalytics {
        val events = mutableListOf<ProductAnalyticsEvent>()

        override fun track(event: ProductAnalyticsEvent) {
            events += event
        }
    }
}
