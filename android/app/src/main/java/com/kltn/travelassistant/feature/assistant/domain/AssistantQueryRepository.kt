package com.kltn.travelassistant.feature.assistant.domain

interface AssistantQueryRepository {
    suspend fun submit(request: AssistantQueryRequest): AssistantRepositoryResult
}
