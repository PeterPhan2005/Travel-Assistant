package com.kltn.travelassistant.feature.itinerary.data

import com.kltn.travelassistant.data.preferences.ActivePreferenceAccount
import com.kltn.travelassistant.data.preferences.BackendEndpoint
import com.kltn.travelassistant.data.preferences.BackendEndpointProvider
import com.kltn.travelassistant.data.preferences.FirebasePreferenceSession
import com.kltn.travelassistant.data.preferences.PreferenceHttpClient
import com.kltn.travelassistant.data.preferences.PreferenceTokenResult
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.async
import kotlinx.coroutines.cancelAndJoin
import kotlinx.coroutines.delay
import kotlinx.coroutines.test.runTest
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import okhttp3.mockwebserver.SocketPolicy
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test

class SavedItineraryNetworkTest {
    private lateinit var backend: MockWebServer

    @Before
    fun setUp() {
        backend = MockWebServer()
        backend.start()
    }

    @After
    fun tearDown() {
        backend.shutdown()
    }

    @Test
    fun putFetchesTokenAtRequestTimeAndSendsOnlyCanonicalSnapshot() = runTest {
        backend.enqueue(jsonResponse(successBody()))
        val session = FakeSession()

        val result = api(session).synchronize(OWNER_KEY, snapshot())

        assertEquals(ItineraryRemoteResult.Success(1), result)
        assertEquals(listOf(false), session.forceRefreshes)
        val request = backend.takeRequest()
        assertEquals("PUT", request.method)
        assertEquals("/v1/itineraries/$ITINERARY_ID", request.path)
        assertEquals("Bearer token-0", request.getHeader("Authorization"))
        val body = request.body.readUtf8()
        assertTrue(body.contains("\"base_revision\":0"))
        assertTrue(body.contains("\"position\":0"))
        assertFalse(body.contains("owner"))
        assertFalse(body.contains("account"))
        assertFalse(body.contains("latitude"))
        assertFalse(body.contains("longitude"))
        assertFalse(body.contains("notes"))
        assertFalse(body.contains("token-0"))
    }

    @Test
    fun one401ForcesExactlyOneRefreshAndNoOtherHttpRetryOccurs() = runTest {
        backend.enqueue(MockResponse().setResponseCode(401))
        backend.enqueue(jsonResponse(successBody()))
        val session = FakeSession()

        assertEquals(
            ItineraryRemoteResult.Success(1),
            api(session).synchronize(OWNER_KEY, snapshot()),
        )
        assertEquals(listOf(false, true), session.forceRefreshes)
        assertEquals("Bearer token-0", backend.takeRequest().getHeader("Authorization"))
        assertEquals("Bearer token-1", backend.takeRequest().getHeader("Authorization"))

        backend.enqueue(MockResponse().setResponseCode(503))
        val requestCountBefore = backend.requestCount
        assertEquals(
            ItineraryRemoteResult.RetryableFailure,
            api(session).synchronize(OWNER_KEY, snapshot()),
        )
        assertEquals(requestCountBefore + 1, backend.requestCount)
    }

    @Test
    fun conflictAndInvalidResponseAreStableTerminalResults() = runTest {
        backend.enqueue(MockResponse().setResponseCode(409))
        backend.enqueue(jsonResponse(successBody().replace("\"revision\":1", "\"revision\":7")))
        val api = api(FakeSession())

        assertEquals(ItineraryRemoteResult.Conflict, api.synchronize(OWNER_KEY, snapshot()))
        assertEquals(ItineraryRemoteResult.InvalidData, api.synchronize(OWNER_KEY, snapshot()))
    }

    @Test
    fun deleteSendsOnlyRevisionAndAcceptsIdempotentTombstoneRevision() = runTest {
        backend.enqueue(
            jsonResponse(
                """{"id":"$ITINERARY_ID","revision":3,"deleted":true}""",
            ),
        )

        val result = api(FakeSession()).synchronize(
            OWNER_KEY,
            snapshot().copy(
                localRevision = 2,
                serverRevision = 1,
                deleted = true,
                title = "",
                city = "",
                localDate = "",
                timezone = "",
                startLocalTime = "",
                endLocalTime = "",
                items = emptyList(),
                assumptions = emptyList(),
                warnings = emptyList(),
            ),
        )

        assertEquals(ItineraryRemoteResult.Success(3), result)
        val request = backend.takeRequest()
        assertEquals("DELETE", request.method)
        assertEquals("{\"base_revision\":1}", request.body.readUtf8())
    }

    @Test
    fun cancellationCancelsTheInFlightCallAndPropagates() = runTest {
        backend.enqueue(MockResponse().setSocketPolicy(SocketPolicy.NO_RESPONSE))
        val request = async {
            api(FakeSession()).synchronize(OWNER_KEY, snapshot())
        }
        while (backend.requestCount == 0) delay(10)

        request.cancel(CancellationException("test cancellation"))
        request.cancelAndJoin()

        assertTrue(request.isCancelled)
    }

    private fun api(session: FirebasePreferenceSession) = OkHttpSavedItineraryApi(
        PreferenceHttpClient(),
        object : BackendEndpointProvider {
            override fun endpointOrNull() = BackendEndpoint(backend.url("/"))
        },
        session,
        SavedItineraryNetworkCodec(),
    )

    private fun snapshot() = SavedItinerarySyncSnapshot(
        id = ITINERARY_ID,
        localRevision = 1,
        serverRevision = 0,
        deleted = false,
        title = "Một ngày ở Quận 1",
        city = "hcmc",
        localDate = "2026-08-01",
        timezone = "Asia/Ho_Chi_Minh",
        startLocalTime = "09:00",
        endLocalTime = "17:00",
        items = listOf(
            SavedItinerarySyncItem(
                id = ITEM_ID,
                position = 0,
                title = "Bưu điện Trung tâm",
                startLocalTime = "09:00",
                endLocalTime = "10:00",
            ),
        ),
        assumptions = listOf("Đi bộ giữa các điểm gần nhau."),
        warnings = emptyList(),
    )

    private fun successBody() =
        """{"id":"$ITINERARY_ID","revision":1,"title":"Một ngày ở Quận 1","city":"hcmc","local_date":"2026-08-01","timezone":"Asia/Ho_Chi_Minh","start_local_time":"09:00:00","end_local_time":"17:00:00","items":[{"id":"$ITEM_ID","position":0,"title":"Bưu điện Trung tâm","start_local_time":"09:00:00","end_local_time":"10:00:00"}],"assumptions":["Đi bộ giữa các điểm gần nhau."],"warnings":[]}"""

    private fun jsonResponse(body: String) = MockResponse()
        .setResponseCode(200)
        .setHeader("Content-Type", "application/json; charset=utf-8")
        .setBody(body)

    private class FakeSession : FirebasePreferenceSession {
        val forceRefreshes = mutableListOf<Boolean>()

        override fun currentVerifiedAccount() = ActivePreferenceAccount(OWNER_KEY)

        override suspend fun idToken(
            expectedOwnerKey: String,
            forceRefresh: Boolean,
        ): PreferenceTokenResult {
            assertEquals(OWNER_KEY, expectedOwnerKey)
            forceRefreshes += forceRefresh
            return PreferenceTokenResult.Success(if (forceRefresh) "token-1" else "token-0")
        }
    }

    private companion object {
        const val OWNER_KEY =
            "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
        const val ITINERARY_ID = "00000000-0000-4000-8000-000000000071"
        const val ITEM_ID = "00000000-0000-4000-8000-000000000072"
    }
}
