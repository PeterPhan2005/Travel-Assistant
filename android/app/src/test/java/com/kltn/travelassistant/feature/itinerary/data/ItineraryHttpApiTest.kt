package com.kltn.travelassistant.feature.itinerary.data

import com.kltn.travelassistant.data.preferences.ActivePreferenceAccount
import com.kltn.travelassistant.data.preferences.BackendEndpoint
import com.kltn.travelassistant.data.preferences.BackendEndpointProvider
import com.kltn.travelassistant.data.preferences.FirebasePreferenceSession
import com.kltn.travelassistant.data.preferences.PreferenceTokenResult
import com.kltn.travelassistant.feature.itinerary.readItineraryContractFixture
import com.kltn.travelassistant.feature.itinerary.domain.ItineraryCity
import com.kltn.travelassistant.feature.itinerary.domain.ItineraryDraftFailure
import com.kltn.travelassistant.feature.itinerary.domain.ItineraryDraftGenerationResult
import com.kltn.travelassistant.feature.itinerary.domain.ItineraryDraftRequest
import com.kltn.travelassistant.feature.itinerary.domain.ItineraryLocationSnapshot
import com.kltn.travelassistant.feature.itinerary.domain.isValidDraftForRequest
import java.time.LocalDate
import java.time.LocalTime
import java.util.concurrent.TimeUnit
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.async
import kotlinx.coroutines.delay
import kotlinx.coroutines.test.runTest
import okhttp3.OkHttpClient
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import okhttp3.mockwebserver.SocketPolicy
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test

class ItineraryHttpApiTest {
    private lateinit var server: MockWebServer
    private lateinit var tokens: FakeTokenProvider
    private lateinit var api: OkHttpItineraryApi

    @Before
    fun setUp() {
        server = MockWebServer()
        server.start()
        tokens = FakeTokenProvider()
        api = apiFor(server, tokens)
    }

    @After
    fun tearDown() {
        server.shutdown()
    }

    @Test
    fun exactEndpointHcmcFieldsNotesCoordinatesAndNoInternalData() = runTest {
        server.enqueue(jsonResponse(successBody()))

        api.generate(
            OWNER_KEY,
            request(
                notes = PRIVATE_NOTE,
                currentLocation = ItineraryLocationSnapshot(10.776, 106.7),
            ),
        )

        val recorded = server.takeRequest()
        assertEquals("POST", recorded.method)
        assertEquals("/v1/itinerary-drafts/generate", recorded.path)
        assertEquals("application/json", recorded.getHeader("Accept"))
        assertEquals("Bearer ephemeral-token", recorded.getHeader("Authorization"))
        val body = recorded.body.readUtf8()
        assertEquals(
            """{"city":"hcmc","local_date":"2026-08-01","timezone":"Asia/Ho_Chi_Minh","start_local_time":"09:00","end_local_time":"17:00","maximum_stops":4,"notes":"$PRIVATE_NOTE","locale":"vi-VN","client_mode":"online","latitude":10.776,"longitude":106.7}""",
            body,
        )
        for (forbidden in listOf("audio", "transcript", "candidate", "evidence", "source_id", "claim_id", "saved_itinerary_id")) {
            assertFalse(body.contains(forbidden))
        }
        assertEquals(listOf(false), tokens.forceRefreshes)
    }

    @Test
    fun bangkokAndAbsentOptionalValuesMapExactly() = runTest {
        server.enqueue(
            jsonResponse(
                readItineraryContractFixture(
                    "t062_itinerary_partial_bangkok.json",
                ),
            ),
        )

        val request = request(
            city = ItineraryCity.BANGKOK,
            timezone = "Asia/Bangkok",
            localDate = LocalDate.of(2026, 8, 2),
            maximumStops = 2,
            notes = null,
            currentLocation = null,
        )
        val result = api.generate(
            OWNER_KEY,
            request,
        )

        val body = server.takeRequest().body.readUtf8()
        assertTrue(body.contains("\"city\":\"bkk\""))
        assertTrue(body.contains("\"notes\":null"))
        assertTrue(body.contains("\"latitude\":null,\"longitude\":null"))
        val draft = (result as ItineraryDraftGenerationResult.Success).draft
        assertEquals(ItineraryCity.BANGKOK, draft.city)
        assertEquals("Asia/Bangkok", draft.timezone)
        assertEquals(
            listOf("Cảnh báo thử nghiệm an toàn."),
            draft.warnings.map { it.message },
        )
        assertTrue(isValidDraftForRequest(draft, request))
    }

    @Test
    fun exactBackendProducedHcmcSuccessPassesFinalT070Validation() = runTest {
        val body = readItineraryContractFixture(
            "t062_itinerary_success_hcmc.json",
        )
        server.enqueue(jsonResponse(body))
        val request = request(
            localDate = LocalDate.of(2026, 8, 2),
            maximumStops = 2,
        )

        val result = api.generate(OWNER_KEY, request)

        val draft = (result as ItineraryDraftGenerationResult.Success).draft
        assertEquals(ItineraryCity.HO_CHI_MINH_CITY, draft.city)
        assertEquals(LocalDate.of(2026, 8, 2), draft.localDate)
        assertEquals(LocalTime.of(9, 0), draft.startLocalTime)
        assertEquals(LocalTime.of(17, 0), draft.endLocalTime)
        assertEquals(
            listOf("Giả định thử nghiệm an toàn."),
            draft.assumptions,
        )
        assertEquals(2, draft.items.size)
        assertTrue(isValidDraftForRequest(draft, request))
    }

    @Test
    fun one401RefreshesOnceAndASecond401Stops() = runTest {
        server.enqueue(MockResponse().setResponseCode(401))
        server.enqueue(jsonResponse(successBody()))
        api.generate(OWNER_KEY, request())
        assertEquals(listOf(false, true), tokens.forceRefreshes)
        assertEquals(2, server.requestCount)

        tokens.forceRefreshes.clear()
        server.enqueue(MockResponse().setResponseCode(401))
        server.enqueue(MockResponse().setResponseCode(401))
        val failure = expectFailure { api.generate(OWNER_KEY, request()) }
        assertEquals(ItineraryDraftFailure.AUTHENTICATION_REQUIRED, failure.reason)
        assertEquals(listOf(false, true), tokens.forceRefreshes)
        assertEquals(4, server.requestCount)
    }

    @Test
    fun firebaseTokenIsFetchedImmediatelyBeforeEveryHttpAttempt() = runTest {
        val events = mutableListOf<String>()
        val orderedTokens = FakeTokenProvider(events)
        val orderedClient = OkHttpClient.Builder()
            .addNetworkInterceptor { chain ->
                events += "http"
                chain.proceed(chain.request())
            }
            .build()
        val orderedApi = apiFor(
            server,
            orderedTokens,
            ItineraryHttpClient(orderedClient),
        )
        server.enqueue(MockResponse().setResponseCode(401))
        server.enqueue(jsonResponse(successBody()))

        orderedApi.generate(OWNER_KEY, request())

        assertEquals(listOf("token:false", "http", "token:true", "http"), events)
    }

    @Test
    fun rateLimitServerFailureAndInvalidResponseNeverRetry() = runTest {
        listOf(
            429 to ItineraryDraftFailure.RATE_LIMITED,
            503 to ItineraryDraftFailure.UNAVAILABLE,
        ).forEach { (status, expected) ->
            val before = server.requestCount
            tokens.forceRefreshes.clear()
            server.enqueue(MockResponse().setResponseCode(status))
            assertEquals(expected, expectFailure { api.generate(OWNER_KEY, request()) }.reason)
            assertEquals(before + 1, server.requestCount)
            assertEquals(listOf(false), tokens.forceRefreshes)
        }

        val before = server.requestCount
        server.enqueue(jsonResponse(successBody().replace("\"retryable\":false", "\"retryable\":false,\"trace_id\":\"private\"")))
        assertEquals(
            ItineraryDraftFailure.INVALID_RESPONSE,
            expectFailure { api.generate(OWNER_KEY, request()) }.reason,
        )
        assertEquals(before + 1, server.requestCount)
    }

    @Test
    fun nonJsonAndOversizedResponsesFailClosedWithoutRetry() = runTest {
        server.enqueue(
            MockResponse()
                .setHeader("Content-Type", "text/plain")
                .setBody(successBody()),
        )
        assertEquals(
            ItineraryDraftFailure.INVALID_RESPONSE,
            expectFailure { api.generate(OWNER_KEY, request()) }.reason,
        )

        server.enqueue(jsonResponse("x".repeat(70_000)))
        assertEquals(
            ItineraryDraftFailure.INVALID_RESPONSE,
            expectFailure { api.generate(OWNER_KEY, request()) }.reason,
        )
        assertEquals(2, server.requestCount)
    }

    @Test
    fun timeoutDoesNotRetryAndCancellationCancelsTheCall() = runTest {
        val timeoutServer = MockWebServer()
        timeoutServer.start()
        try {
            timeoutServer.enqueue(MockResponse().setSocketPolicy(SocketPolicy.NO_RESPONSE))
            val timeoutApi = apiFor(
                timeoutServer,
                tokens,
                ItineraryHttpClient(
                    OkHttpClient.Builder()
                        .callTimeout(100, TimeUnit.MILLISECONDS)
                        .retryOnConnectionFailure(false)
                        .build(),
                ),
            )
            assertEquals(
                ItineraryDraftFailure.TIMEOUT,
                expectFailure { timeoutApi.generate(OWNER_KEY, request()) }.reason,
            )
            assertEquals(1, timeoutServer.requestCount)
        } finally {
            timeoutServer.shutdown()
        }

        server.enqueue(MockResponse().setSocketPolicy(SocketPolicy.NO_RESPONSE))
        val call = async { api.generate(OWNER_KEY, request()) }
        while (server.requestCount == 0) delay(10)
        call.cancel()
        assertTrue(call.isCancelled)
        try {
            call.await()
        } catch (_: CancellationException) {
            assertTrue(true)
        }
    }

    @Test
    fun successPartialAndFailedResponsesMapToClosedDomainResults() = runTest {
        val codec = ItineraryJsonCodec()
        val success = codec.decodeResponse(successBody())
        assertTrue(success is ItineraryDraftGenerationResult.Success)

        val partial = codec.decodeResponse(
            successBody(status = "partial", warnings = "[\"Kiểm tra giờ mở cửa.\"]"),
        ) as ItineraryDraftGenerationResult.Success
        assertEquals("Kiểm tra giờ mở cửa.", partial.draft.warnings.single().message)

        val failed = codec.decodeResponse(failedBody())
        assertEquals(
            ItineraryDraftGenerationResult.Failure(
                ItineraryDraftFailure.INVALID_RESPONSE,
            ),
            failed,
        )
    }

    @Test
    fun responseTimesFailClosedUnlessTheyMatchCanonicalWholeMinuteWireFormat() {
        val codec = ItineraryJsonCodec()

        listOf(
            successBody().replace("09:00:00", "09:00"),
            successBody().replace("12:00:00", "12:00:01"),
            successBody().replace("17:00:00", "17:00:00.000000"),
        ).forEach { body ->
            try {
                codec.decodeResponse(body)
                throw AssertionError("Expected InvalidItineraryJsonException")
            } catch (_: InvalidItineraryJsonException) {
                assertTrue(true)
            }
        }
    }

    private fun apiFor(
        backend: MockWebServer,
        tokenProvider: FirebasePreferenceSession,
        httpClient: ItineraryHttpClient = ItineraryHttpClient(),
    ) = OkHttpItineraryApi(
        httpClient,
        object : BackendEndpointProvider {
            override fun endpointOrNull() = BackendEndpoint(backend.url("/"))
        },
        tokenProvider,
        ItineraryJsonCodec(),
    )

    private fun request(
        city: ItineraryCity = ItineraryCity.HO_CHI_MINH_CITY,
        timezone: String = "Asia/Ho_Chi_Minh",
        localDate: LocalDate = LocalDate.of(2026, 8, 1),
        maximumStops: Int = 4,
        notes: String? = null,
        currentLocation: ItineraryLocationSnapshot? = null,
    ) = ItineraryDraftRequest(
        city = city,
        localDate = localDate,
        timezone = timezone,
        startLocalTime = LocalTime.of(9, 0),
        endLocalTime = LocalTime.of(17, 0),
        maximumStops = maximumStops,
        notes = notes,
        currentLocation = currentLocation,
    )

    private fun jsonResponse(body: String) = MockResponse()
        .setHeader("Content-Type", "application/json; charset=utf-8")
        .setBody(body)

    private fun successBody(
        status: String = "success",
        city: String = "hcmc",
        timezone: String = "Asia/Ho_Chi_Minh",
        warnings: String = "[]",
    ) = """
        {"status":"$status","city":"$city","local_date":"2026-08-01","timezone":"$timezone","start_local_time":"09:00:00","end_local_time":"17:00:00","items":[{"start_local_time":"09:00:00","end_local_time":"12:00:00","title":"Bưu điện"}],"assumptions":["Lịch trình nháp."],"warnings":$warnings,"failure_category":null,"retryable":false}
    """.trimIndent()

    private fun failedBody() =
        """{"status":"failed","city":"hcmc","local_date":"2026-08-01","timezone":"Asia/Ho_Chi_Minh","start_local_time":"09:00:00","end_local_time":"17:00:00","items":[],"assumptions":[],"warnings":[],"failure_category":"insufficient_candidates","retryable":false}"""

    private suspend fun expectFailure(
        block: suspend () -> Unit,
    ): ItineraryApiException = try {
        block()
        throw AssertionError("Expected ItineraryApiException")
    } catch (exception: ItineraryApiException) {
        exception
    }

    private class FakeTokenProvider(
        private val events: MutableList<String>? = null,
    ) : FirebasePreferenceSession {
        val forceRefreshes = mutableListOf<Boolean>()

        override fun currentVerifiedAccount() = ActivePreferenceAccount(OWNER_KEY)

        override suspend fun idToken(
            expectedOwnerKey: String,
            forceRefresh: Boolean,
        ): PreferenceTokenResult {
            assertEquals(OWNER_KEY, expectedOwnerKey)
            forceRefreshes += forceRefresh
            events?.add("token:$forceRefresh")
            return PreferenceTokenResult.Success("ephemeral-token")
        }
    }

    private companion object {
        const val OWNER_KEY =
            "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
        const val PRIVATE_NOTE = "Không ăn cay"
    }
}
