package com.kltn.travelassistant.feature.assistant.data

import com.kltn.travelassistant.feature.assistant.domain.AssistantIntent
import com.kltn.travelassistant.feature.assistant.domain.AssistantIntentAnalytics
import com.kltn.travelassistant.feature.assistant.domain.AssistantIntentOutcome
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
internal class NoOpAssistantIntentAnalytics @Inject constructor() : AssistantIntentAnalytics {
    override fun record(
        intent: AssistantIntent,
        outcome: AssistantIntentOutcome,
    ) = Unit
}
