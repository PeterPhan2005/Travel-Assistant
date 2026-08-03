package com.kltn.travelassistant.feature.itinerary.data

import com.kltn.travelassistant.data.preferences.BackendEndpointProvider
import com.kltn.travelassistant.data.preferences.FirebasePreferenceSession
import com.kltn.travelassistant.data.preferences.PreferenceTokenResult
import com.kltn.travelassistant.feature.itinerary.domain.ItineraryDraftFailure
import com.kltn.travelassistant.feature.itinerary.domain.ItineraryDraftGenerationResult
import com.kltn.travelassistant.feature.itinerary.domain.ItineraryDraftRequest
import java.io.ByteArrayOutputStream
import java.io.IOException
import java.io.InterruptedIOException
import java.net.SocketTimeoutException
import java.nio.ByteBuffer
import java.nio.charset.CodingErrorAction
import java.nio.charset.StandardCharsets
import java.util.concurrent.TimeUnit
import javax.inject.Inject
import javax.inject.Singleton
import kotlinx.coroutines.suspendCancellableCoroutine
import okhttp3.Call
import okhttp3.Callback
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import okhttp3.Response
import kotlin.coroutines.resume
import kotlin.coroutines.resumeWithException

internal class ItineraryApiException(
    val reason: ItineraryDraftFailure,
) : Exception(reason.name)

internal interface ItineraryHttpApi {
    suspend fun generate(
        ownerKey: String,
        request: ItineraryDraftRequest,
    ): ItineraryDraftGenerationResult
}

@Singleton
internal class ItineraryHttpClient @Inject constructor() {
    var client: OkHttpClient = OkHttpClient.Builder()
        .connectTimeout(15, TimeUnit.SECONDS)
        .readTimeout(25, TimeUnit.SECONDS)
        .writeTimeout(15, TimeUnit.SECONDS)
        .callTimeout(30, TimeUnit.SECONDS)
        .followRedirects(false)
        .followSslRedirects(false)
        .retryOnConnectionFailure(false)
        .build()
        private set

    internal constructor(client: OkHttpClient) : this() {
        this.client = client
    }
}

@Singleton
internal class OkHttpItineraryApi @Inject constructor(
    httpClient: ItineraryHttpClient,
    private val endpointProvider: BackendEndpointProvider,
    private val tokenProvider: FirebasePreferenceSession,
    private val codec: ItineraryJsonCodec,
) : ItineraryHttpApi {
    private val client = httpClient.client

    override suspend fun generate(
        ownerKey: String,
        request: ItineraryDraftRequest,
    ): ItineraryDraftGenerationResult {
        val endpoint = endpointProvider.endpointOrNull()
            ?: throw ItineraryApiException(ItineraryDraftFailure.UNAVAILABLE)
        val url = endpoint.baseUrl.resolve(ITINERARY_PATH)
            ?: throw ItineraryApiException(ItineraryDraftFailure.UNAVAILABLE)
        if (
            endpoint.baseUrl.scheme != url.scheme ||
            endpoint.baseUrl.host != url.host ||
            endpoint.baseUrl.port != url.port
        ) {
            throw ItineraryApiException(ItineraryDraftFailure.UNAVAILABLE)
        }
        val body = try {
            codec.encodeRequest(request)
        } catch (_: InvalidItineraryJsonException) {
            throw ItineraryApiException(ItineraryDraftFailure.INVALID_REQUEST)
        }
        val bytes = body.toByteArray(StandardCharsets.UTF_8)
        if (bytes.size > MAX_REQUEST_BYTES) {
            throw ItineraryApiException(ItineraryDraftFailure.INVALID_REQUEST)
        }

        repeat(MAX_AUTH_ATTEMPTS) { attempt ->
            val token = when (
                val tokenResult = tokenProvider.idToken(
                    expectedOwnerKey = ownerKey,
                    forceRefresh = attempt > 0,
                )
            ) {
                PreferenceTokenResult.AuthenticationFailure ->
                    throw ItineraryApiException(
                        ItineraryDraftFailure.AUTHENTICATION_REQUIRED,
                    )
                PreferenceTokenResult.RetryableFailure ->
                    throw ItineraryApiException(ItineraryDraftFailure.UNAVAILABLE)
                is PreferenceTokenResult.Success -> tokenResult.token
            }
            val httpRequest = Request.Builder()
                .url(url)
                .header("Accept", JSON_MEDIA_TYPE_STRING)
                .header("Authorization", "Bearer $token")
                .post(bytes.toRequestBody(JSON_MEDIA_TYPE))
                .build()
            val response = executeCall(httpRequest)
            if (response.code == 401) {
                if (attempt + 1 < MAX_AUTH_ATTEMPTS) return@repeat
                throw ItineraryApiException(
                    ItineraryDraftFailure.AUTHENTICATION_REQUIRED,
                )
            }
            return try {
                codec.decodeResponse(requireNotNull(response.body))
            } catch (_: InvalidItineraryJsonException) {
                throw ItineraryApiException(ItineraryDraftFailure.INVALID_RESPONSE)
            }
        }
        throw ItineraryApiException(ItineraryDraftFailure.AUTHENTICATION_REQUIRED)
    }

    private suspend fun executeCall(request: Request): RawItineraryResponse {
        return try {
            awaitCall(client.newCall(request))
        } catch (_: SocketTimeoutException) {
            throw ItineraryApiException(ItineraryDraftFailure.TIMEOUT)
        } catch (_: InterruptedIOException) {
            throw ItineraryApiException(ItineraryDraftFailure.TIMEOUT)
        } catch (_: IOException) {
            throw ItineraryApiException(ItineraryDraftFailure.UNAVAILABLE)
        }
    }

    private suspend fun awaitCall(call: Call): RawItineraryResponse =
        suspendCancellableCoroutine { continuation ->
            continuation.invokeOnCancellation { call.cancel() }
            call.enqueue(
                object : Callback {
                    override fun onFailure(call: Call, e: IOException) {
                        if (continuation.isActive) continuation.resumeWithException(e)
                    }

                    override fun onResponse(call: Call, response: Response) {
                        if (!continuation.isActive) {
                            response.close()
                            return
                        }
                        try {
                            response.use {
                                val raw = if (response.code == 401) {
                                    RawItineraryResponse(401, null)
                                } else {
                                    classifyResponse(response)
                                    RawItineraryResponse(
                                        response.code,
                                        readBoundedUtf8(response),
                                    )
                                }
                                continuation.resume(raw)
                            }
                        } catch (exception: Exception) {
                            if (continuation.isActive) {
                                continuation.resumeWithException(exception)
                            }
                        }
                    }
                },
            )
        }

    private fun classifyResponse(response: Response) {
        when {
            response.code == 200 -> Unit
            response.code == 401 || response.code == 403 ->
                throw ItineraryApiException(
                    ItineraryDraftFailure.AUTHENTICATION_REQUIRED,
                )
            response.code == 408 ->
                throw ItineraryApiException(ItineraryDraftFailure.TIMEOUT)
            response.code == 429 ->
                throw ItineraryApiException(ItineraryDraftFailure.RATE_LIMITED)
            response.code in setOf(400, 405, 409, 422) ->
                throw ItineraryApiException(ItineraryDraftFailure.INVALID_REQUEST)
            response.code in 500..599 ->
                throw ItineraryApiException(ItineraryDraftFailure.UNAVAILABLE)
            else -> throw ItineraryApiException(ItineraryDraftFailure.INVALID_RESPONSE)
        }
        val contentType = response.body.contentType()
        if (
            contentType == null ||
            contentType.type != "application" ||
            contentType.subtype != "json" ||
            contentType.charset(StandardCharsets.UTF_8) != StandardCharsets.UTF_8
        ) {
            throw ItineraryApiException(ItineraryDraftFailure.INVALID_RESPONSE)
        }
    }

    private fun readBoundedUtf8(response: Response): String {
        val body = response.body
        val declaredLength = body.contentLength()
        if (declaredLength > MAX_RESPONSE_BYTES || declaredLength < -1) {
            throw ItineraryApiException(ItineraryDraftFailure.INVALID_RESPONSE)
        }
        val bytes = body.byteStream().use { input ->
            val output = ByteArrayOutputStream()
            val buffer = ByteArray(DEFAULT_BUFFER_SIZE)
            while (true) {
                val read = input.read(buffer)
                if (read == -1) break
                if (output.size().toLong() + read > MAX_RESPONSE_BYTES) {
                    throw ItineraryApiException(ItineraryDraftFailure.INVALID_RESPONSE)
                }
                output.write(buffer, 0, read)
            }
            output.toByteArray()
        }
        return try {
            StandardCharsets.UTF_8.newDecoder()
                .onMalformedInput(CodingErrorAction.REPORT)
                .onUnmappableCharacter(CodingErrorAction.REPORT)
                .decode(ByteBuffer.wrap(bytes))
                .toString()
        } catch (_: Exception) {
            throw ItineraryApiException(ItineraryDraftFailure.INVALID_RESPONSE)
        }
    }

    private companion object {
        const val ITINERARY_PATH = "v1/itinerary-drafts/generate"
        const val MAX_AUTH_ATTEMPTS = 2
        const val MAX_REQUEST_BYTES = 4_096
        const val MAX_RESPONSE_BYTES = 65_536L
        const val JSON_MEDIA_TYPE_STRING = "application/json"
        val JSON_MEDIA_TYPE = "$JSON_MEDIA_TYPE_STRING; charset=utf-8".toMediaType()
    }

    private data class RawItineraryResponse(val code: Int, val body: String?)
}
