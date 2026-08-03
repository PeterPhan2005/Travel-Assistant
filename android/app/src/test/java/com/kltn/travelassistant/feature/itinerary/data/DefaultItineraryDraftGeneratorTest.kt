package com.kltn.travelassistant.feature.itinerary.data

import com.kltn.travelassistant.data.preferences.ActivePreferenceAccount
import com.kltn.travelassistant.data.preferences.FirebasePreferenceSession
import com.kltn.travelassistant.data.preferences.PreferenceTokenResult
import com.kltn.travelassistant.feature.itinerary.domain.ItineraryCity
import com.kltn.travelassistant.feature.itinerary.domain.ItineraryDraftFailure
import com.kltn.travelassistant.feature.itinerary.domain.ItineraryDraftGenerationResult
import com.kltn.travelassistant.feature.itinerary.domain.ItineraryDraftRequest
import java.time.LocalDate
import java.time.LocalTime
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Test

class DefaultItineraryDraftGeneratorTest {
    @Test
    fun signedOutSessionStartsNoRequest() = runTest {
        val api = FakeApi()
        val generator = DefaultItineraryDraftGenerator(FakeSession(null), api)

        val result = generator.generate(request())

        assertEquals(
            ItineraryDraftGenerationResult.Failure(
                ItineraryDraftFailure.AUTHENTICATION_REQUIRED,
            ),
            result,
        )
        assertEquals(0, api.callCount)
    }

    @Test
    fun verifiedOwnerIsPassedAndClosedApiFailureIsMapped() = runTest {
        val api = FakeApi(ItineraryDraftFailure.TIMEOUT)
        val generator = DefaultItineraryDraftGenerator(
            FakeSession(ActivePreferenceAccount(OWNER_KEY)),
            api,
        )

        val result = generator.generate(request())

        assertEquals(
            ItineraryDraftGenerationResult.Failure(ItineraryDraftFailure.TIMEOUT),
            result,
        )
        assertEquals(OWNER_KEY, api.ownerKey)
        assertEquals(1, api.callCount)
    }

    private class FakeApi(
        private val failure: ItineraryDraftFailure? = null,
    ) : ItineraryHttpApi {
        var callCount = 0
        var ownerKey: String? = null

        override suspend fun generate(
            ownerKey: String,
            request: ItineraryDraftRequest,
        ): ItineraryDraftGenerationResult {
            callCount += 1
            this.ownerKey = ownerKey
            if (failure != null) throw ItineraryApiException(failure)
            throw CancellationException()
        }
    }

    private class FakeSession(
        private val account: ActivePreferenceAccount?,
    ) : FirebasePreferenceSession {
        override fun currentVerifiedAccount(): ActivePreferenceAccount? = account

        override suspend fun idToken(
            expectedOwnerKey: String,
            forceRefresh: Boolean,
        ): PreferenceTokenResult = error("token access belongs to the HTTP boundary")
    }

    private fun request() = ItineraryDraftRequest(
        city = ItineraryCity.HO_CHI_MINH_CITY,
        localDate = LocalDate.of(2026, 8, 1),
        timezone = "Asia/Ho_Chi_Minh",
        startLocalTime = LocalTime.of(9, 0),
        endLocalTime = LocalTime.of(17, 0),
        maximumStops = 4,
        notes = null,
        currentLocation = null,
    )

    private companion object {
        const val OWNER_KEY =
            "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
    }
}
