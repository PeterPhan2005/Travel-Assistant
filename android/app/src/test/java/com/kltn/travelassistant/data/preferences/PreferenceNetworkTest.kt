package com.kltn.travelassistant.data.preferences

import com.kltn.travelassistant.feature.preferences.domain.PreferenceDocument
import java.util.concurrent.TimeUnit
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.async
import kotlinx.coroutines.delay
import kotlinx.coroutines.test.runTest
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
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

class PreferenceNetworkTest {
    private lateinit var server: MockWebServer
    private lateinit var tokens: FakeTokenProvider
    private lateinit var api: OkHttpPreferenceApi

    @Before
    fun setUp() {
        server = MockWebServer()
        server.start()
        tokens = FakeTokenProvider()
        api = apiFor(server, tokens)
    }

    @Test
    fun backendEndpointPolicyAllowsOnlyHttpsOrApprovedDebugLoopback() {
        assertEquals(
            "https://api.example.com/",
            BackendEndpointPolicy.endpointOrNull(
                raw = "https://api.example.com/",
                allowDebugLoopback = false,
            )?.baseUrl.toString(),
        )
        assertNull(
            BackendEndpointPolicy.endpointOrNull(
                raw = "http://127.0.0.1:8000/",
                allowDebugLoopback = false,
            ),
        )
        listOf("10.0.2.2", "127.0.0.1").forEach { host ->
            assertEquals(
                host,
                BackendEndpointPolicy.endpointOrNull(
                    raw = "http://$host:8000/",
                    allowDebugLoopback = true,
                )?.baseUrl?.host,
            )
        }
        listOf(
            "http://localhost:8000/",
            "http://192.168.1.10:8000/",
            "http://example.com/",
            "https://api.example.com/path",
            "https://user:password@api.example.com/",
        ).forEach { raw ->
            assertNull(
                BackendEndpointPolicy.endpointOrNull(
                    raw = raw,
                    allowDebugLoopback = true,
                ),
            )
        }
    }

    @After
    fun tearDown() {
        server.shutdown()
    }

    @Test
    fun validGetAndPutUseJsonAndBearerOnlyOnBackendOrigin() = runTest {
        server.enqueue(jsonResponse("""{"schema_version":1,"preferences":{},"updated_at":null}"""))
        server.enqueue(
            jsonResponse(
                """{"schema_version":1,"preferences":{"neutral":"Tiếng Việt"},"updated_at":"2026-07-28T02:03:04Z"}""",
            ),
        )

        val get = api.get(OWNER_KEY)
        val put = api.put(
            OWNER_KEY,
            PreferenceDocument(
                preferences = JsonObject(mapOf("neutral" to JsonPrimitive("Tiếng Việt"))),
            ),
        )

        assertEquals(null, get.updatedAt)
        assertEquals("2026-07-28T02:03:04Z", put.updatedAt)
        val getRequest = server.takeRequest()
        val putRequest = server.takeRequest()
        assertEquals("/preferences", getRequest.path)
        assertEquals("Bearer ephemeral-token", getRequest.getHeader("Authorization"))
        assertEquals("application/json", getRequest.getHeader("Accept"))
        assertEquals("PUT", putRequest.method)
        assertTrue(putRequest.body.readUtf8().contains("Tiếng Việt"))
        assertEquals(listOf(false, false), tokens.forceRefreshes)
    }

    @Test
    fun one401ForcesExactlyOneRefreshAndSecond401Fails() = runTest {
        server.enqueue(MockResponse().setResponseCode(401))
        server.enqueue(MockResponse().setResponseCode(401))

        val failure = expectApiException { api.get(OWNER_KEY) }

        assertEquals(PreferenceApiError.AUTHENTICATION, failure.error)
        assertEquals(listOf(false, true), tokens.forceRefreshes)
        assertEquals(2, server.requestCount)
    }

    @Test
    fun redirectOversizedWrongMediaAndMalformedJsonFailClosed() = runTest {
        server.enqueue(
            MockResponse()
                .setResponseCode(302)
                .setHeader("Location", "https://example.invalid/preferences"),
        )
        assertEquals(
            PreferenceApiError.INVALID_RESPONSE,
            expectApiException { api.get(OWNER_KEY) }.error,
        )
        assertEquals(1, server.requestCount)

        server.enqueue(jsonResponse("x".repeat(40_000)))
        assertEquals(
            PreferenceApiError.INVALID_RESPONSE,
            expectApiException { api.get(OWNER_KEY) }.error,
        )

        server.enqueue(MockResponse().setBody("{}").setHeader("Content-Type", "text/plain"))
        assertEquals(
            PreferenceApiError.INVALID_RESPONSE,
            expectApiException { api.get(OWNER_KEY) }.error,
        )

        server.enqueue(jsonResponse("""{"schema_version":1"""))
        assertEquals(
            PreferenceApiError.INVALID_RESPONSE,
            expectApiException { api.get(OWNER_KEY) }.error,
        )
    }

    @Test
    fun cancellationPropagatesWithoutReturningTypedFailure() = runTest {
        server.enqueue(MockResponse().setSocketPolicy(SocketPolicy.NO_RESPONSE))

        val request = async { api.get(OWNER_KEY) }
        while (server.requestCount == 0) delay(10)
        request.cancel()

        assertTrue(request.isCancelled)
        try {
            request.await()
        } catch (exception: CancellationException) {
            assertTrue(true)
        }
    }

    @Test
    fun tokenFailureContainsNoOwnerTokenOrDocument() = runTest {
        tokens.result = PreferenceTokenResult.AuthenticationFailure

        val failure = expectApiException {
            api.put(
                OWNER_KEY,
                PreferenceDocument(
                    preferences = JsonObject(mapOf(PRIVATE_VALUE to JsonPrimitive(PRIVATE_VALUE))),
                ),
            )
        }

        val text = failure.toString()
        assertFalse(text.contains(OWNER_KEY))
        assertFalse(text.contains("ephemeral-token"))
        assertFalse(text.contains(PRIVATE_VALUE))
        assertNull(failure.cause)
        assertEquals(0, server.requestCount)
    }

    private fun apiFor(
        backend: MockWebServer,
        tokenProvider: FirebasePreferenceSession,
    ): OkHttpPreferenceApi = OkHttpPreferenceApi(
        httpClient = PreferenceHttpClient(),
        endpointProvider = object : BackendEndpointProvider {
            override fun endpointOrNull() = BackendEndpoint(backend.url("/"))
        },
        tokenProvider = tokenProvider,
        codec = PreferenceDocumentCodec(),
    )

    private fun jsonResponse(body: String): MockResponse = MockResponse()
        .setHeader("Content-Type", "application/json")
        .setBody(body)

    private suspend fun expectApiException(
        block: suspend () -> Unit,
    ): PreferenceApiException = try {
        block()
        throw AssertionError("Expected PreferenceApiException")
    } catch (exception: PreferenceApiException) {
        exception
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
        const val PRIVATE_VALUE = "private-document-fragment"
    }
}
