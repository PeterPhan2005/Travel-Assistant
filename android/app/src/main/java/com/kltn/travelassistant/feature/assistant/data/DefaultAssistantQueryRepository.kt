package com.kltn.travelassistant.feature.assistant.data

import com.kltn.travelassistant.data.preferences.FirebasePreferenceSession
import com.kltn.travelassistant.feature.assistant.domain.AssistantQueryFailure
import com.kltn.travelassistant.feature.assistant.domain.AssistantQueryRepository
import com.kltn.travelassistant.feature.assistant.domain.AssistantQueryRequest
import com.kltn.travelassistant.feature.assistant.domain.AssistantRepositoryResult
import javax.inject.Inject
import javax.inject.Singleton
import kotlinx.coroutines.CancellationException

@Singleton
internal class DefaultAssistantQueryRepository @Inject constructor(
    private val session: FirebasePreferenceSession,
    private val api: AssistantHttpApi,
) : AssistantQueryRepository {
    override suspend fun submit(
        request: AssistantQueryRequest,
    ): AssistantRepositoryResult {
        val account = session.currentVerifiedAccount()
            ?: return AssistantRepositoryResult.Failure(
                AssistantQueryFailure.AUTHENTICATION_REQUIRED,
            )
        return try {
            AssistantRepositoryResult.Structured(
                api.query(account.ownerKey, request),
            )
        } catch (exception: CancellationException) {
            throw exception
        } catch (exception: AssistantApiException) {
            AssistantRepositoryResult.Failure(exception.reason)
        } catch (_: Exception) {
            AssistantRepositoryResult.Failure(
                AssistantQueryFailure.INVALID_RESPONSE,
            )
        }
    }
}
