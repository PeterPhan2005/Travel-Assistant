package com.kltn.travelassistant.data.preferences

import com.kltn.travelassistant.BuildConfig
import java.io.ByteArrayOutputStream
import java.io.IOException
import java.nio.ByteBuffer
import java.nio.charset.CodingErrorAction
import java.nio.charset.StandardCharsets
import java.util.concurrent.TimeUnit
import javax.inject.Inject
import javax.inject.Singleton
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ensureActive
import kotlinx.coroutines.job
import kotlinx.coroutines.withContext
import okhttp3.Call
import okhttp3.HttpUrl
import okhttp3.HttpUrl.Companion.toHttpUrlOrNull
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import okhttp3.Response

internal data class BackendEndpoint(
    val baseUrl: HttpUrl,
)

internal interface BackendEndpointProvider {
    fun endpointOrNull(): BackendEndpoint?
}

@Singleton
internal class BuildConfigBackendEndpointProvider @Inject constructor() :
    BackendEndpointProvider {
    override fun endpointOrNull(): BackendEndpoint? {
        val raw = BuildConfig.BACKEND_BASE_URL
        if (raw.isBlank()) return null
        val url = raw.toHttpUrlOrNull() ?: return null
        if (
            url.username.isNotEmpty() ||
            url.password.isNotEmpty() ||
            url.query != null ||
            url.fragment != null ||
            url.encodedPath != "/"
        ) {
            return null
        }
        val allowedScheme = url.scheme == "https" || (
            BuildConfig.DEBUG &&
                url.scheme == "http" &&
                url.host == DEBUG_EMULATOR_HOST
            )
        return if (allowedScheme) BackendEndpoint(url) else null
    }

    private companion object {
        const val DEBUG_EMULATOR_HOST = "10.0.2.2"
    }
}

internal enum class PreferenceApiError {
    RETRYABLE,
    AUTHENTICATION,
    INVALID_DOCUMENT,
    INVALID_RESPONSE,
    CONFIGURATION,
}

internal class PreferenceApiException(
    val error: PreferenceApiError,
) : Exception(error.name)

internal interface PreferenceApi {
    suspend fun get(ownerKey: String): ServerPreferenceDocument

    suspend fun put(
        ownerKey: String,
        document: com.kltn.travelassistant.feature.preferences.domain.PreferenceDocument,
    ): ServerPreferenceDocument
}

@Singleton
internal class PreferenceHttpClient @Inject constructor() {
    val client: OkHttpClient = OkHttpClient.Builder()
        .connectTimeout(15, TimeUnit.SECONDS)
        .readTimeout(20, TimeUnit.SECONDS)
        .callTimeout(30, TimeUnit.SECONDS)
        .followRedirects(false)
        .followSslRedirects(false)
        .retryOnConnectionFailure(false)
        .build()
}

@Singleton
internal class OkHttpPreferenceApi @Inject constructor(
    httpClient: PreferenceHttpClient,
    private val endpointProvider: BackendEndpointProvider,
    private val tokenProvider: FirebasePreferenceSession,
    private val codec: PreferenceDocumentCodec,
) : PreferenceApi {
    private val client = httpClient.client

    override suspend fun get(ownerKey: String): ServerPreferenceDocument =
        execute(ownerKey = ownerKey, method = "GET", body = null)

    override suspend fun put(
        ownerKey: String,
        document: com.kltn.travelassistant.feature.preferences.domain.PreferenceDocument,
    ): ServerPreferenceDocument {
        val body = try {
            codec.encodeRequest(document)
        } catch (exception: InvalidPreferenceDocumentException) {
            throw PreferenceApiException(PreferenceApiError.INVALID_DOCUMENT)
        }
        return execute(ownerKey = ownerKey, method = "PUT", body = body)
    }

    private suspend fun execute(
        ownerKey: String,
        method: String,
        body: String?,
    ): ServerPreferenceDocument {
        val endpoint = endpointProvider.endpointOrNull()
            ?: throw PreferenceApiException(PreferenceApiError.CONFIGURATION)
        val url = endpoint.baseUrl.resolve("preferences")
            ?: throw PreferenceApiException(PreferenceApiError.CONFIGURATION)
        if (!sameOrigin(endpoint.baseUrl, url)) {
            throw PreferenceApiException(PreferenceApiError.CONFIGURATION)
        }

        repeat(MAX_AUTH_ATTEMPTS) { attempt ->
            val token = when (
                val tokenResult = tokenProvider.idToken(
                    expectedOwnerKey = ownerKey,
                    forceRefresh = attempt > 0,
                )
            ) {
                PreferenceTokenResult.AuthenticationFailure ->
                    throw PreferenceApiException(PreferenceApiError.AUTHENTICATION)
                PreferenceTokenResult.RetryableFailure ->
                    throw PreferenceApiException(PreferenceApiError.RETRYABLE)
                is PreferenceTokenResult.Success -> tokenResult.token
            }
            val request = Request.Builder()
                .url(url)
                .header("Accept", JSON_MEDIA_TYPE_STRING)
                .header("Authorization", "Bearer $token")
                .apply {
                    if (method == "GET") {
                        get()
                    } else {
                        put(
                            requireNotNull(body).toRequestBody(JSON_MEDIA_TYPE),
                        )
                    }
                }
                .build()
            val response = executeCall(request)
            if (response.code == 401) {
                if (attempt + 1 < MAX_AUTH_ATTEMPTS) return@repeat
                throw PreferenceApiException(PreferenceApiError.AUTHENTICATION)
            }
            return try {
                codec.decodeResponse(requireNotNull(response.body))
            } catch (exception: InvalidPreferenceDocumentException) {
                throw PreferenceApiException(PreferenceApiError.INVALID_RESPONSE)
            }
        }
        throw PreferenceApiException(PreferenceApiError.AUTHENTICATION)
    }

    private suspend fun executeCall(request: Request): RawPreferenceResponse =
        withContext(Dispatchers.IO) {
            val call: Call = client.newCall(request)
            val cancellation = coroutineContext.job.invokeOnCompletion {
                call.cancel()
            }
            try {
                coroutineContext.ensureActive()
                call.execute().use { response ->
                    if (response.code == 401) {
                        RawPreferenceResponse(code = 401, body = null)
                    } else {
                        classifyResponse(response)
                        RawPreferenceResponse(
                            code = response.code,
                            body = readBoundedUtf8(response),
                        )
                    }
                }
            } catch (exception: IOException) {
                coroutineContext.ensureActive()
                throw PreferenceApiException(PreferenceApiError.RETRYABLE)
            } finally {
                cancellation.dispose()
            }
        }

    private fun classifyResponse(response: Response) {
        when {
            response.code == 200 -> Unit
            response.code == 403 ->
                throw PreferenceApiException(PreferenceApiError.AUTHENTICATION)
            response.code in RETRYABLE_STATUS_CODES || response.code in 500..599 ->
                throw PreferenceApiException(PreferenceApiError.RETRYABLE)
            response.code in 400..499 ->
                throw PreferenceApiException(PreferenceApiError.INVALID_DOCUMENT)
            else -> throw PreferenceApiException(PreferenceApiError.INVALID_RESPONSE)
        }
        val contentType = response.body.contentType()
        if (
            contentType == null ||
            contentType.type != "application" ||
            contentType.subtype != "json"
        ) {
            throw PreferenceApiException(PreferenceApiError.INVALID_RESPONSE)
        }
    }

    private fun readBoundedUtf8(response: Response): String {
        val body = response.body
        val declaredLength = body.contentLength()
        if (declaredLength > MAX_RESPONSE_BYTES || declaredLength < -1) {
            throw PreferenceApiException(PreferenceApiError.INVALID_RESPONSE)
        }
        val bytes = body.byteStream().use { input ->
            val output = ByteArrayOutputStream()
            val buffer = ByteArray(DEFAULT_BUFFER_SIZE)
            while (true) {
                val read = input.read(buffer)
                if (read == -1) break
                if (output.size().toLong() + read > MAX_RESPONSE_BYTES) {
                    throw PreferenceApiException(PreferenceApiError.INVALID_RESPONSE)
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
        } catch (exception: Exception) {
            throw PreferenceApiException(PreferenceApiError.INVALID_RESPONSE)
        }
    }

    private fun sameOrigin(base: HttpUrl, target: HttpUrl): Boolean =
        base.scheme == target.scheme &&
            base.host == target.host &&
            base.port == target.port

    private companion object {
        const val MAX_AUTH_ATTEMPTS = 2
        const val MAX_RESPONSE_BYTES = 32_768L
        const val JSON_MEDIA_TYPE_STRING = "application/json"
        val JSON_MEDIA_TYPE = JSON_MEDIA_TYPE_STRING.toMediaType()
        val RETRYABLE_STATUS_CODES = setOf(408, 425, 429)
    }

    private data class RawPreferenceResponse(
        val code: Int,
        val body: String?,
    )
}
