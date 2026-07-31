package com.kltn.travelassistant.feature.assistant.data

import com.kltn.travelassistant.data.preferences.ActivePreferenceAccount
import com.kltn.travelassistant.data.preferences.BackendEndpoint
import com.kltn.travelassistant.data.preferences.BackendEndpointProvider
import com.kltn.travelassistant.data.preferences.FirebasePreferenceSession
import com.kltn.travelassistant.data.preferences.PreferenceTokenResult
import com.kltn.travelassistant.feature.assistant.domain.AssistantLocationSnapshot
import com.kltn.travelassistant.feature.assistant.domain.AssistantQueryFailure
import com.kltn.travelassistant.feature.assistant.domain.AssistantQueryRequest
import java.net.SocketTimeoutException
import java.util.concurrent.TimeUnit
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.async
import kotlinx.coroutines.delay
import kotlinx.coroutines.test.runTest
import okio.Buffer
import okhttp3.OkHttpClient
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import okhttp3.mockwebserver.SocketPolicy
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test

class AssistantHttpApiTest {
    private lateinit var server: MockWebServer
    private lateinit var tokens: FakeTokenProvider
    private lateinit var api: OkHttpAssistantApi

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
    fun postUsesExactSameOriginPathJsonOnlyAndEphemeralBearer() = runTest {
        server.enqueue(jsonResponse(successBody()))

        val result = api.query(
            OWNER_KEY,
            AssistantQueryRequest(
                text = PRIVATE_QUERY,
                location = AssistantLocationSnapshot(10.776, 106.7),
            ),
        )

        assertEquals("Xin chào", result.message)
        val request = server.takeRequest()
        assertEquals("POST", request.method)
        assertEquals("/v1/assistant/query", request.path)
        assertEquals("application/json", request.getHeader("Accept"))
        assertEquals("Bearer ephemeral-token", request.getHeader("Authorization"))
        assertTrue(request.getHeader("Content-Type")!!.startsWith("application/json"))
        val body = request.body.readUtf8()
        assertTrue(body.contains(PRIVATE_QUERY))
        assertTrue(body.contains(""""locale":"vi-VN""""))
        assertTrue(body.contains(""""client_mode":"online""""))
        assertTrue(body.contains(""""trip_id":null"""))
        assertTrue(body.contains(""""latitude":10.776"""))
        assertFalse(body.contains("audio", ignoreCase = true))
        assertFalse(body.contains("file", ignoreCase = true))
        assertFalse(body.contains("recording", ignoreCase = true))
        assertEquals(listOf(false), tokens.forceRefreshes)
    }

    @Test
    fun one401ForcesOneRefreshAndNoOtherStatusRetries() = runTest {
        server.enqueue(MockResponse().setResponseCode(401))
        server.enqueue(jsonResponse(successBody()))
        api.query(OWNER_KEY, request())

        assertEquals(listOf(false, true), tokens.forceRefreshes)
        assertEquals(2, server.requestCount)

        tokens.forceRefreshes.clear()
        server.enqueue(MockResponse().setResponseCode(503))
        val failure = expectApiException { api.query(OWNER_KEY, request()) }
        assertEquals(AssistantQueryFailure.UNAVAILABLE, failure.reason)
        assertEquals(listOf(false), tokens.forceRefreshes)
        assertEquals(3, server.requestCount)
    }

    @Test
    fun timeoutAndRateLimitHaveClosedMappings() = runTest {
        val timeoutServer = MockWebServer()
        timeoutServer.start()
        try {
            timeoutServer.enqueue(MockResponse().setSocketPolicy(SocketPolicy.NO_RESPONSE))
            val timeoutClient = OkHttpClient.Builder()
                .callTimeout(100, TimeUnit.MILLISECONDS)
                .retryOnConnectionFailure(false)
                .build()
            val timeoutApi = apiFor(
                timeoutServer,
                tokens,
                AssistantHttpClient(timeoutClient),
            )
            assertEquals(
                AssistantQueryFailure.TIMEOUT,
                expectApiException {
                    timeoutApi.query(OWNER_KEY, request())
                }.reason,
            )
        } finally {
            timeoutServer.shutdown()
        }

        server.enqueue(MockResponse().setResponseCode(429))
        assertEquals(
            AssistantQueryFailure.RATE_LIMITED,
            expectApiException { api.query(OWNER_KEY, request()) }.reason,
        )
    }

    @Test
    fun wrongMediaOversizedMalformedUtf8AndUnknownJsonFailClosed() = runTest {
        server.enqueue(
            MockResponse()
                .setHeader("Content-Type", "text/plain")
                .setBody(successBody()),
        )
        assertInvalidResponse()

        server.enqueue(jsonResponse("x".repeat(70_000)))
        assertInvalidResponse()

        server.enqueue(
            MockResponse()
                .setHeader("Content-Type", "application/json; charset=utf-8")
                .setBody(Buffer().write(byteArrayOf(0xC3.toByte(), 0x28))),
        )
        assertInvalidResponse()

        server.enqueue(
            jsonResponse(
                successBody().replace(
                    """"retryable": false""",
                    """"retryable": false,"internal_stage":"router"""",
                ),
            ),
        )
        assertInvalidResponse()
    }

    @Test
    fun redirectIsNotFollowedAndConfigurationCannotChangeOrigin() = runTest {
        server.enqueue(
            MockResponse()
                .setResponseCode(302)
                .setHeader("Location", "https://example.invalid/steal"),
        )

        val failure = expectApiException { api.query(OWNER_KEY, request()) }

        assertEquals(AssistantQueryFailure.INVALID_RESPONSE, failure.reason)
        assertEquals(1, server.requestCount)
    }

    @Test
    fun cancellationCancelsActiveOkHttpCall() = runTest {
        server.enqueue(MockResponse().setSocketPolicy(SocketPolicy.NO_RESPONSE))
        val call = async { api.query(OWNER_KEY, request()) }
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
    fun tokenFailureContainsNoQueryCoordinateTokenOrOwner() = runTest {
        tokens.result = PreferenceTokenResult.AuthenticationFailure

        val failure = expectApiException {
            api.query(
                OWNER_KEY,
                AssistantQueryRequest(
                    text = PRIVATE_QUERY,
                    location = AssistantLocationSnapshot(10.776, 106.7),
                ),
            )
        }

        val text = failure.toString()
        assertFalse(text.contains(PRIVATE_QUERY))
        assertFalse(text.contains(OWNER_KEY))
        assertFalse(text.contains("ephemeral-token"))
        assertFalse(text.contains("10.776"))
        assertNull(failure.cause)
        assertEquals(0, server.requestCount)
    }

    private suspend fun assertInvalidResponse() {
        assertEquals(
            AssistantQueryFailure.INVALID_RESPONSE,
            expectApiException { api.query(OWNER_KEY, request()) }.reason,
        )
    }

    private fun request() = AssistantQueryRequest(
        text = "Một câu hỏi",
        location = null,
    )

    private fun apiFor(
        backend: MockWebServer,
        tokenProvider: FirebasePreferenceSession,
        httpClient: AssistantHttpClient = AssistantHttpClient(),
    ): OkHttpAssistantApi = OkHttpAssistantApi(
        httpClient = httpClient,
        endpointProvider = object : BackendEndpointProvider {
            override fun endpointOrNull() = BackendEndpoint(backend.url("/"))
        },
        tokenProvider = tokenProvider,
        codec = AssistantJsonCodec(),
    )

    private fun jsonResponse(body: String): MockResponse = MockResponse()
        .setHeader("Content-Type", "application/json; charset=utf-8")
        .setBody(body)

    private fun successBody(): String =
        """
        {
          "request_id": "request-one",
          "status": "success",
          "intent": "general_travel_help",
          "message": "Xin chào",
          "poi_results": [],
          "narration": null,
          "itinerary": null,
          "sources": [],
          "warnings": [],
          "retryable": false
        }
        """.trimIndent()

    private suspend fun expectApiException(
        block: suspend () -> Unit,
    ): AssistantApiException = try {
        block()
        throw AssertionError("Expected AssistantApiException")
    } catch (exception: AssistantApiException) {
        exception
    } catch (exception: SocketTimeoutException) {
        throw AssertionError("Raw timeout escaped", exception)
    }

    private class FakeTokenProvider : FirebasePreferenceSession {
        var result: PreferenceTokenResult =
            PreferenceTokenResult.Success("ephemeral-token")
        val forceRefreshes = mutableListOf<Boolean>()

        override fun currentVerifiedAccount(): ActivePreferenceAccount =
            ActivePreferenceAccount(OWNER_KEY)

        override suspend fun idToken(
            expectedOwnerKey: String,
            forceRefresh: Boolean,
        ): PreferenceTokenResult {
            assertEquals(OWNER_KEY, expectedOwnerKey)
            forceRefreshes += forceRefresh
            return result
        }
    }

    private companion object {
        const val OWNER_KEY =
            "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
        const val PRIVATE_QUERY = "Tôi muốn ăn phở riêng tư"
    }
}
