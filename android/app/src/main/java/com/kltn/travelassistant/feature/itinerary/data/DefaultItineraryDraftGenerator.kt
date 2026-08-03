package com.kltn.travelassistant.feature.itinerary.data

import com.kltn.travelassistant.data.preferences.FirebasePreferenceSession
import com.kltn.travelassistant.feature.itinerary.domain.ItineraryDraftFailure
import com.kltn.travelassistant.feature.itinerary.domain.ItineraryDraftGenerationResult
import com.kltn.travelassistant.feature.itinerary.domain.ItineraryDraftGenerator
import com.kltn.travelassistant.feature.itinerary.domain.ItineraryDraftRequest
import javax.inject.Inject
import javax.inject.Singleton
import kotlinx.coroutines.CancellationException

@Singleton
internal class DefaultItineraryDraftGenerator @Inject constructor(
    private val session: FirebasePreferenceSession,
    private val api: ItineraryHttpApi,
) : ItineraryDraftGenerator {
    override suspend fun generate(
        request: ItineraryDraftRequest,
    ): ItineraryDraftGenerationResult {
        val account = session.currentVerifiedAccount()
            ?: return ItineraryDraftGenerationResult.Failure(
                ItineraryDraftFailure.AUTHENTICATION_REQUIRED,
            )
        return try {
            api.generate(account.ownerKey, request)
        } catch (exception: CancellationException) {
            throw exception
        } catch (exception: ItineraryApiException) {
            ItineraryDraftGenerationResult.Failure(exception.reason)
        } catch (_: Exception) {
            ItineraryDraftGenerationResult.Failure(
                ItineraryDraftFailure.INVALID_RESPONSE,
            )
        }
    }
}
