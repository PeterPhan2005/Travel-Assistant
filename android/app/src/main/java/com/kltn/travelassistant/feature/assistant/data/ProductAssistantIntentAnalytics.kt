package com.kltn.travelassistant.feature.assistant.data

import com.kltn.travelassistant.analytics.AnalyticsAssistantIntent
import com.kltn.travelassistant.analytics.ProductAnalytics
import com.kltn.travelassistant.analytics.ProductAnalyticsEvent
import com.kltn.travelassistant.analytics.VoiceIntentOutcome
import com.kltn.travelassistant.analytics.trackSafely
import com.kltn.travelassistant.feature.assistant.domain.AssistantIntent
import com.kltn.travelassistant.feature.assistant.domain.AssistantIntentAnalytics
import com.kltn.travelassistant.feature.assistant.domain.AssistantIntentInputMode
import com.kltn.travelassistant.feature.assistant.domain.AssistantIntentOutcome
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
internal class ProductAssistantIntentAnalytics @Inject constructor(
    private val productAnalytics: ProductAnalytics,
) : AssistantIntentAnalytics {
    override fun record(
        intent: AssistantIntent,
        outcome: AssistantIntentOutcome,
        inputMode: AssistantIntentInputMode,
    ) {
        if (inputMode != AssistantIntentInputMode.VOICE) return
        productAnalytics.trackSafely(
            ProductAnalyticsEvent.VoiceIntentResult(
                intent = intent.toAnalyticsIntent(),
                outcome = outcome.toAnalyticsOutcome(),
            ),
        )
    }
}

private fun AssistantIntent.toAnalyticsIntent(): AnalyticsAssistantIntent = when (this) {
    AssistantIntent.NEARBY_DISCOVERY -> AnalyticsAssistantIntent.NEARBY_DISCOVERY
    AssistantIntent.POI_INFORMATION -> AnalyticsAssistantIntent.POI_INFORMATION
    AssistantIntent.LOCAL_CULTURE -> AnalyticsAssistantIntent.LOCAL_CULTURE
    AssistantIntent.ITINERARY_DRAFTING -> AnalyticsAssistantIntent.ITINERARY_DRAFTING
    AssistantIntent.GENERAL_TRAVEL_HELP -> AnalyticsAssistantIntent.GENERAL_TRAVEL_HELP
    AssistantIntent.UNSUPPORTED -> AnalyticsAssistantIntent.UNSUPPORTED
}

private fun AssistantIntentOutcome.toAnalyticsOutcome(): VoiceIntentOutcome = when (this) {
    AssistantIntentOutcome.SUCCESS -> VoiceIntentOutcome.SUCCESS
    AssistantIntentOutcome.PARTIAL -> VoiceIntentOutcome.PARTIAL
    AssistantIntentOutcome.FAILED -> VoiceIntentOutcome.FAILED
}
