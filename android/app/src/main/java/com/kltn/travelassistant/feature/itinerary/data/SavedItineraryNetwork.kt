package com.kltn.travelassistant.feature.itinerary.data

import com.kltn.travelassistant.data.preferences.BackendEndpointProvider
import com.kltn.travelassistant.data.preferences.FirebasePreferenceSession
import com.kltn.travelassistant.data.preferences.PreferenceHttpClient
import com.kltn.travelassistant.data.preferences.PreferenceTokenResult
import java.io.ByteArrayOutputStream
import java.io.IOException
import java.nio.ByteBuffer
import java.nio.charset.CodingErrorAction
import java.nio.charset.StandardCharsets
import javax.inject.Inject
import javax.inject.Singleton
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ensureActive
import kotlinx.coroutines.job
import kotlinx.coroutines.withContext
import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import kotlinx.serialization.SerializationException
import kotlinx.serialization.encodeToString
import okhttp3.Call
import okhttp3.HttpUrl
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import okhttp3.Response

internal data class SavedItinerarySyncItem(
    val id: String,
    val position: Int,
    val title: String,
    val startLocalTime: String,
    val endLocalTime: String,
)

internal data class SavedItinerarySyncSnapshot(
    val id: String,
    val localRevision: Long,
    val serverRevision: Long,
    val deleted: Boolean,
    val title: String,
    val city: String,
    val localDate: String,
    val timezone: String,
    val startLocalTime: String,
    val endLocalTime: String,
    val items: List<SavedItinerarySyncItem>,
    val assumptions: List<String>,
    val warnings: List<String>,
)

internal sealed interface ItineraryRemoteResult {
    data class Success(val serverRevision: Long) : ItineraryRemoteResult

    data object Conflict : ItineraryRemoteResult

    data object RetryableFailure : ItineraryRemoteResult

    data object AuthenticationFailure : ItineraryRemoteResult

    data object InvalidData : ItineraryRemoteResult
}

internal interface SavedItineraryApi {
    suspend fun synchronize(
        ownerKey: String,
        snapshot: SavedItinerarySyncSnapshot,
    ): ItineraryRemoteResult
}

@Serializable
private data class ItineraryItemWire(
    val id: String,
    val position: Int,
    val title: String,
    @SerialName("start_local_time")
    val startLocalTime: String,
    @SerialName("end_local_time")
    val endLocalTime: String,
)

@Serializable
private data class ItineraryPutRequestWire(
    @SerialName("base_revision")
    val baseRevision: Long,
    val title: String,
    val city: String,
    @SerialName("local_date")
    val localDate: String,
    val timezone: String,
    @SerialName("start_local_time")
    val startLocalTime: String,
    @SerialName("end_local_time")
    val endLocalTime: String,
    val items: List<ItineraryItemWire>,
    val assumptions: List<String>,
    val warnings: List<String>,
)

@Serializable
private data class ItineraryResponseWire(
    val id: String,
    val revision: Long,
    val title: String,
    val city: String,
    @SerialName("local_date")
    val localDate: String,
    val timezone: String,
    @SerialName("start_local_time")
    val startLocalTime: String,
    @SerialName("end_local_time")
    val endLocalTime: String,
    val items: List<ItineraryItemWire>,
    val assumptions: List<String>,
    val warnings: List<String>,
)

@Serializable
private data class ItineraryDeleteRequestWire(
    @SerialName("base_revision")
    val baseRevision: Long,
)

@Serializable
private data class ItineraryDeleteResponseWire(
    val id: String,
    val revision: Long,
    val deleted: Boolean,
)

internal class SavedItineraryNetworkCodec(
    private val json: kotlinx.serialization.json.Json = strictSavedItineraryJson(),
) {
    fun encodePut(snapshot: SavedItinerarySyncSnapshot): String =
        json.encodeToString(snapshot.toPutWire())

    fun encodeDelete(snapshot: SavedItinerarySyncSnapshot): String =
        json.encodeToString(ItineraryDeleteRequestWire(snapshot.serverRevision))

    fun decodePutResponse(
        raw: String,
        snapshot: SavedItinerarySyncSnapshot,
    ): Long {
        val response = decode<ItineraryResponseWire>(raw)
        val expected = snapshot.toPutWire()
        if (
            response.id != snapshot.id ||
            response.revision != snapshot.serverRevision + 1 ||
            response.title != expected.title ||
            response.city != expected.city ||
            response.localDate != expected.localDate ||
            response.timezone != expected.timezone ||
            response.startLocalTime != expected.startLocalTime.toServerTime() ||
            response.endLocalTime != expected.endLocalTime.toServerTime() ||
            response.items != expected.items.map { item ->
                item.copy(
                    startLocalTime = item.startLocalTime.toServerTime(),
                    endLocalTime = item.endLocalTime.toServerTime(),
                )
            } ||
            response.assumptions != expected.assumptions ||
            response.warnings != expected.warnings
        ) {
            throw InvalidSavedItineraryException()
        }
        return response.revision
    }

    fun decodeDeleteResponse(
        raw: String,
        snapshot: SavedItinerarySyncSnapshot,
    ): Long {
        val response = decode<ItineraryDeleteResponseWire>(raw)
        if (
            response.id != snapshot.id ||
            !response.deleted ||
            response.revision <= snapshot.serverRevision
        ) {
            throw InvalidSavedItineraryException()
        }
        return response.revision
    }

    private inline fun <reified T> decode(raw: String): T = try {
        json.decodeFromString(raw)
    } catch (exception: SerializationException) {
        throw InvalidSavedItineraryException()
    } catch (exception: IllegalArgumentException) {
        throw InvalidSavedItineraryException()
    }
}

@Singleton
internal class OkHttpSavedItineraryApi @Inject constructor(
    httpClient: PreferenceHttpClient,
    private val endpointProvider: BackendEndpointProvider,
    private val session: FirebasePreferenceSession,
    private val codec: SavedItineraryNetworkCodec,
) : SavedItineraryApi {
    private val client: OkHttpClient = httpClient.client

    override suspend fun synchronize(
        ownerKey: String,
        snapshot: SavedItinerarySyncSnapshot,
    ): ItineraryRemoteResult {
        val endpoint = endpointProvider.endpointOrNull()
            ?: return ItineraryRemoteResult.InvalidData
        val url = endpoint.baseUrl.resolve("v1/itineraries/${snapshot.id}")
            ?: return ItineraryRemoteResult.InvalidData
        if (!sameOrigin(endpoint.baseUrl, url)) return ItineraryRemoteResult.InvalidData
        val body = try {
            if (snapshot.deleted) codec.encodeDelete(snapshot) else codec.encodePut(snapshot)
        } catch (exception: InvalidSavedItineraryException) {
            return ItineraryRemoteResult.InvalidData
        }

        repeat(MAX_AUTH_ATTEMPTS) { attempt ->
            val token = when (
                val tokenResult = session.idToken(
                    expectedOwnerKey = ownerKey,
                    forceRefresh = attempt > 0,
                )
            ) {
                PreferenceTokenResult.AuthenticationFailure ->
                    return ItineraryRemoteResult.AuthenticationFailure
                PreferenceTokenResult.RetryableFailure ->
                    return ItineraryRemoteResult.RetryableFailure
                is PreferenceTokenResult.Success -> tokenResult.token
            }
            val request = Request.Builder()
                .url(url)
                .header("Accept", JSON_MEDIA_TYPE_STRING)
                .header("Authorization", "Bearer $token")
                .method(
                    if (snapshot.deleted) "DELETE" else "PUT",
                    body.toRequestBody(JSON_MEDIA_TYPE),
                )
                .build()
            val raw = try {
                executeCall(request)
            } catch (exception: RetryableItineraryNetworkException) {
                return ItineraryRemoteResult.RetryableFailure
            } catch (exception: InvalidItineraryNetworkException) {
                return ItineraryRemoteResult.InvalidData
            }
            when (raw.code) {
                401 -> if (attempt + 1 < MAX_AUTH_ATTEMPTS) return@repeat else {
                    return ItineraryRemoteResult.AuthenticationFailure
                }
                409 -> return ItineraryRemoteResult.Conflict
                200 -> return try {
                    val revision = if (snapshot.deleted) {
                        codec.decodeDeleteResponse(requireNotNull(raw.body), snapshot)
                    } else {
                        codec.decodePutResponse(requireNotNull(raw.body), snapshot)
                    }
                    ItineraryRemoteResult.Success(revision)
                } catch (exception: InvalidSavedItineraryException) {
                    ItineraryRemoteResult.InvalidData
                }
                in RETRYABLE_STATUS_CODES,
                in 500..599,
                -> return ItineraryRemoteResult.RetryableFailure
                else -> return ItineraryRemoteResult.InvalidData
            }
        }
        return ItineraryRemoteResult.AuthenticationFailure
    }

    private suspend fun executeCall(request: Request): RawItineraryResponse =
        withContext(Dispatchers.IO) {
            val call: Call = client.newCall(request)
            val cancellation = coroutineContext.job.invokeOnCompletion { call.cancel() }
            try {
                coroutineContext.ensureActive()
                call.execute().use { response ->
                    if (response.code in setOf(401, 409)) {
                        RawItineraryResponse(response.code, null)
                    } else {
                        if (response.code == 200) validateJson(response)
                        RawItineraryResponse(
                            response.code,
                            if (response.code == 200) readBoundedUtf8(response) else null,
                        )
                    }
                }
            } catch (exception: IOException) {
                coroutineContext.ensureActive()
                throw RetryableItineraryNetworkException()
            } finally {
                cancellation.dispose()
            }
        }

    private fun validateJson(response: Response) {
        val contentType = response.body.contentType()
        if (
            contentType == null ||
            contentType.type != "application" ||
            contentType.subtype != "json"
        ) {
            throw InvalidItineraryNetworkException()
        }
    }

    private fun readBoundedUtf8(response: Response): String {
        val body = response.body
        val declaredLength = body.contentLength()
        if (declaredLength > MAX_RESPONSE_BYTES || declaredLength < -1) {
            throw InvalidItineraryNetworkException()
        }
        val bytes = body.byteStream().use { input ->
            val output = ByteArrayOutputStream()
            val buffer = ByteArray(DEFAULT_BUFFER_SIZE)
            while (true) {
                val read = input.read(buffer)
                if (read == -1) break
                if (output.size().toLong() + read > MAX_RESPONSE_BYTES) {
                    throw InvalidItineraryNetworkException()
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
            throw InvalidItineraryNetworkException()
        }
    }

    private fun sameOrigin(base: HttpUrl, target: HttpUrl): Boolean =
        base.scheme == target.scheme && base.host == target.host && base.port == target.port

    private companion object {
        const val MAX_AUTH_ATTEMPTS = 2
        const val MAX_RESPONSE_BYTES = 65_536L
        const val JSON_MEDIA_TYPE_STRING = "application/json"
        val JSON_MEDIA_TYPE = JSON_MEDIA_TYPE_STRING.toMediaType()
        val RETRYABLE_STATUS_CODES = setOf(408, 425, 429)
    }
}

private class RetryableItineraryNetworkException : Exception()

private class InvalidItineraryNetworkException : Exception()

private data class RawItineraryResponse(
    val code: Int,
    val body: String?,
)

private fun SavedItinerarySyncSnapshot.toPutWire(): ItineraryPutRequestWire =
    ItineraryPutRequestWire(
        baseRevision = serverRevision,
        title = title,
        city = city,
        localDate = localDate,
        timezone = timezone,
        startLocalTime = startLocalTime,
        endLocalTime = endLocalTime,
        items = items.map { item ->
            ItineraryItemWire(
                id = item.id,
                position = item.position,
                title = item.title,
                startLocalTime = item.startLocalTime,
                endLocalTime = item.endLocalTime,
            )
        },
        assumptions = assumptions,
        warnings = warnings,
    )

private fun String.toServerTime(): String = "$this:00"
