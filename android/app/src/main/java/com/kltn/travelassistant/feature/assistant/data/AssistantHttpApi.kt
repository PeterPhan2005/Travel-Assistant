package com.kltn.travelassistant.feature.assistant.data

import com.kltn.travelassistant.data.preferences.BackendEndpointProvider
import com.kltn.travelassistant.data.preferences.FirebasePreferenceSession
import com.kltn.travelassistant.data.preferences.PreferenceTokenResult
import com.kltn.travelassistant.feature.assistant.domain.AssistantQueryFailure
import com.kltn.travelassistant.feature.assistant.domain.AssistantQueryRequest
import com.kltn.travelassistant.feature.assistant.domain.AssistantQueryResult
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

internal class AssistantApiException(
    val reason: AssistantQueryFailure,
) : Exception(reason.name)

internal interface AssistantHttpApi {
    suspend fun query(
        ownerKey: String,
        request: AssistantQueryRequest,
    ): AssistantQueryResult
}

@Singleton
internal class AssistantHttpClient @Inject constructor() {
    var client: OkHttpClient = OkHttpClient.Builder()
        .connectTimeout(15, TimeUnit.SECONDS)
        .readTimeout(25, TimeUnit.SECONDS)
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
internal class OkHttpAssistantApi @Inject constructor(
    httpClient: AssistantHttpClient,
    private val endpointProvider: BackendEndpointProvider,
    private val tokenProvider: FirebasePreferenceSession,
    private val codec: AssistantJsonCodec,
) : AssistantHttpApi {
    private val client = httpClient.client

    override suspend fun query(
        ownerKey: String,
        request: AssistantQueryRequest,
    ): AssistantQueryResult {
        val endpoint = endpointProvider.endpointOrNull()
            ?: throw AssistantApiException(AssistantQueryFailure.CONFIGURATION)
        val url = endpoint.baseUrl.resolve(ASSISTANT_PATH)
            ?: throw AssistantApiException(AssistantQueryFailure.CONFIGURATION)
        if (
            endpoint.baseUrl.scheme != url.scheme ||
            endpoint.baseUrl.host != url.host ||
            endpoint.baseUrl.port != url.port
        ) {
            throw AssistantApiException(AssistantQueryFailure.CONFIGURATION)
        }
        val body = try {
            codec.encodeRequest(request)
        } catch (_: InvalidAssistantJsonException) {
            throw AssistantApiException(AssistantQueryFailure.INVALID_REQUEST)
        }
        val bytes = body.toByteArray(StandardCharsets.UTF_8)
        if (bytes.size > MAX_REQUEST_BYTES) {
            throw AssistantApiException(AssistantQueryFailure.INVALID_REQUEST)
        }

        repeat(MAX_AUTH_ATTEMPTS) { attempt ->
            val token = when (
                val tokenResult = tokenProvider.idToken(
                    expectedOwnerKey = ownerKey,
                    forceRefresh = attempt > 0,
                )
            ) {
                PreferenceTokenResult.AuthenticationFailure ->
                    throw AssistantApiException(
                        AssistantQueryFailure.AUTHENTICATION_REQUIRED,
                    )
                PreferenceTokenResult.RetryableFailure ->
                    throw AssistantApiException(AssistantQueryFailure.UNAVAILABLE)
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
                throw AssistantApiException(
                    AssistantQueryFailure.AUTHENTICATION_REQUIRED,
                )
            }
            return try {
                codec.decodeResponse(requireNotNull(response.body))
            } catch (_: InvalidAssistantJsonException) {
                throw AssistantApiException(AssistantQueryFailure.INVALID_RESPONSE)
            }
        }
        throw AssistantApiException(AssistantQueryFailure.AUTHENTICATION_REQUIRED)
    }

    private suspend fun executeCall(request: Request): RawAssistantResponse {
        return try {
            awaitCall(client.newCall(request))
        } catch (_: SocketTimeoutException) {
            throw AssistantApiException(AssistantQueryFailure.TIMEOUT)
        } catch (_: InterruptedIOException) {
            throw AssistantApiException(AssistantQueryFailure.TIMEOUT)
        } catch (_: IOException) {
            throw AssistantApiException(AssistantQueryFailure.UNAVAILABLE)
        }
    }

    private suspend fun awaitCall(call: Call): RawAssistantResponse =
        suspendCancellableCoroutine { continuation ->
            continuation.invokeOnCancellation { call.cancel() }
            call.enqueue(
                object : Callback {
                    override fun onFailure(call: Call, e: IOException) {
                        if (continuation.isActive) {
                            continuation.resumeWithException(e)
                        }
                    }

                    override fun onResponse(call: Call, response: Response) {
                        if (!continuation.isActive) {
                            response.close()
                            return
                        }
                        try {
                            response.use {
                                val raw = if (response.code == 401) {
                                    RawAssistantResponse(code = 401, body = null)
                                } else {
                                    classifyResponse(response)
                                    RawAssistantResponse(
                                        code = response.code,
                                        body = readBoundedUtf8(response),
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
                throw AssistantApiException(
                    AssistantQueryFailure.AUTHENTICATION_REQUIRED,
                )
            response.code == 408 -> throw AssistantApiException(AssistantQueryFailure.TIMEOUT)
            response.code == 429 ->
                throw AssistantApiException(AssistantQueryFailure.RATE_LIMITED)
            response.code in setOf(400, 405, 409, 422) ->
                throw AssistantApiException(AssistantQueryFailure.INVALID_REQUEST)
            response.code in 500..599 ->
                throw AssistantApiException(AssistantQueryFailure.UNAVAILABLE)
            else -> throw AssistantApiException(AssistantQueryFailure.INVALID_RESPONSE)
        }
        val contentType = response.body.contentType()
        if (
            contentType == null ||
            contentType.type != "application" ||
            contentType.subtype != "json" ||
            contentType.charset(StandardCharsets.UTF_8) != StandardCharsets.UTF_8
        ) {
            throw AssistantApiException(AssistantQueryFailure.INVALID_RESPONSE)
        }
    }

    private fun readBoundedUtf8(response: Response): String {
        val body = response.body
        val declaredLength = body.contentLength()
        if (declaredLength > MAX_RESPONSE_BYTES || declaredLength < -1) {
            throw AssistantApiException(AssistantQueryFailure.INVALID_RESPONSE)
        }
        val bytes = body.byteStream().use { input ->
            val output = ByteArrayOutputStream()
            val buffer = ByteArray(DEFAULT_BUFFER_SIZE)
            while (true) {
                val read = input.read(buffer)
                if (read == -1) break
                if (output.size().toLong() + read > MAX_RESPONSE_BYTES) {
                    throw AssistantApiException(AssistantQueryFailure.INVALID_RESPONSE)
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
            throw AssistantApiException(AssistantQueryFailure.INVALID_RESPONSE)
        }
    }

    private companion object {
        const val ASSISTANT_PATH = "v1/assistant/query"
        const val MAX_AUTH_ATTEMPTS = 2
        const val MAX_REQUEST_BYTES = 4_096
        const val MAX_RESPONSE_BYTES = 65_536L
        const val JSON_MEDIA_TYPE_STRING = "application/json"
        val JSON_MEDIA_TYPE = "$JSON_MEDIA_TYPE_STRING; charset=utf-8".toMediaType()
    }

    private data class RawAssistantResponse(
        val code: Int,
        val body: String?,
    )
}
