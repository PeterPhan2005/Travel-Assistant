package com.kltn.travelassistant.data.packages

import android.content.Context
import dagger.hilt.android.qualifiers.ApplicationContext
import java.io.ByteArrayOutputStream
import java.io.File
import java.io.FileOutputStream
import java.io.IOException
import java.security.MessageDigest
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
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.Response

@Singleton
class PackageHttpClient @Inject constructor() {
    val client: OkHttpClient = OkHttpClient.Builder()
        .connectTimeout(15, TimeUnit.SECONDS)
        .readTimeout(30, TimeUnit.SECONDS)
        .callTimeout(45, TimeUnit.SECONDS)
        .followRedirects(false)
        .followSslRedirects(false)
        .retryOnConnectionFailure(true)
        .build()
}

@Singleton
class PackageStagingStore internal constructor(
    private val rootDirectory: File,
) {
    @Inject
    constructor(
        @ApplicationContext context: Context,
    ) : this(context.filesDir.resolve("travel-packages/staging"))

    fun partFile(manifest: ValidatedPackageManifest): File =
        cityDirectory(manifest.document.city).resolve(
            "${stageStem(manifest)}.data.part",
        )

    fun verifiedFile(manifest: ValidatedPackageManifest): File =
        cityDirectory(manifest.document.city).resolve(
            "${stageStem(manifest)}.data.verified",
        )

    fun promoteToVerified(manifest: ValidatedPackageManifest, partFile: File): File {
        val verifiedFile = verifiedFile(manifest)
        if (verifiedFile.exists() && !verifiedFile.delete()) {
            throw PackageSyncException(PackageSyncError.INVALID_DATA)
        }
        if (!partFile.renameTo(verifiedFile)) {
            throw PackageSyncException(PackageSyncError.INVALID_DATA)
        }
        return verifiedFile
    }

    fun cleanObsolete(manifest: ValidatedPackageManifest) {
        val keep = setOf(partFile(manifest).name, verifiedFile(manifest).name)
        cityDirectory(manifest.document.city).listFiles()
            ?.filterNot { it.name in keep }
            ?.forEach(File::delete)
    }

    fun cleanCity(cityCode: String) {
        cityDirectory(cityCode).listFiles()?.forEach(File::delete)
    }

    private fun cityDirectory(cityCode: String): File {
        require(cityCode.matches(Regex("^[a-z0-9]+$")))
        val directory = rootDirectory.resolve(cityCode)
        if (!directory.exists() && !directory.mkdirs()) {
            throw PackageSyncException(PackageSyncError.INVALID_DATA)
        }
        if (!directory.isDirectory) {
            throw PackageSyncException(PackageSyncError.INVALID_DATA)
        }
        return directory
    }

    private fun stageStem(manifest: ValidatedPackageManifest): String =
        "${manifest.document.packageId}-${manifest.document.contentVersion}-" +
            manifest.document.sha256.take(16)
}

class PackageDownloader @Inject constructor(
    httpClient: PackageHttpClient,
) {
    private val client = httpClient.client

    suspend fun downloadManifest(location: PackageManifestLocation): String {
        val request = Request.Builder()
            .url(location.manifestUrl)
            .header("Accept", "application/json")
            .get()
            .build()
        return execute(request) { response ->
            classifyManifestResponse(response)
            val body = response.body
            val declaredLength = body.contentLength()
            if (
                declaredLength > PackageManifestValidator.MAX_MANIFEST_BYTES ||
                declaredLength < -1
            ) {
                throw PackageSyncException(PackageSyncError.INVALID_MANIFEST)
            }
            val bytes = body.byteStream().use { input ->
                val output = ByteArrayOutputStream()
                val buffer = ByteArray(DEFAULT_BUFFER_SIZE)
                while (true) {
                    val read = input.read(buffer)
                    if (read == -1) break
                    if (output.size().toLong() + read > PackageManifestValidator.MAX_MANIFEST_BYTES) {
                        throw PackageSyncException(PackageSyncError.INVALID_MANIFEST)
                    }
                    output.write(buffer, 0, read)
                }
                output.toByteArray()
            }
            try {
                StandardCharsets.UTF_8.newDecoder()
                    .onMalformedInput(CodingErrorAction.REPORT)
                    .onUnmappableCharacter(CodingErrorAction.REPORT)
                    .decode(ByteBuffer.wrap(bytes))
                    .toString()
            } catch (exception: Exception) {
                throw PackageSyncException(PackageSyncError.INVALID_MANIFEST, exception)
            }
        }
    }

    suspend fun downloadData(
        manifest: ValidatedPackageManifest,
        partFile: File,
    ): File {
        val expectedSize = manifest.document.byteSize
        if (partFile.length() > expectedSize) {
            partFile.delete()
            throw PackageSyncException(PackageSyncError.INVALID_DATA)
        }
        if (partFile.length() == expectedSize) return partFile

        val existingSize = partFile.length()
        val request = Request.Builder()
            .url(manifest.dataUrl)
            .header("Accept", "application/json")
            .apply {
                if (existingSize > 0) {
                    header("Range", "bytes=$existingSize-")
                }
            }
            .get()
            .build()

        return execute(request) { response ->
            classifyDataResponse(response)
            val append = when (response.code) {
                206 -> {
                    validatePartialResponse(
                        response = response,
                        expectedStart = existingSize,
                        expectedTotal = expectedSize,
                    )
                    true
                }
                200 -> false
                else -> throw PackageSyncException(PackageSyncError.INVALID_DATA)
            }
            val startingSize = if (append) existingSize else 0L
            val declaredLength = response.body.contentLength()
            if (
                declaredLength > expectedSize - startingSize ||
                declaredLength < -1
            ) {
                if (!append) partFile.delete()
                throw PackageSyncException(PackageSyncError.INVALID_DATA)
            }

            try {
                streamResponse(
                    response = response,
                    destination = partFile,
                    append = append,
                    startingSize = startingSize,
                    expectedSize = expectedSize,
                )
            } catch (exception: PackageSyncException) {
                throw exception
            } catch (exception: IOException) {
                throw PackageSyncException(PackageSyncError.NETWORK_UNAVAILABLE, exception)
            }

            when {
                partFile.length() == expectedSize -> partFile
                response.code == 206 || declaredLength == -1L ->
                    throw PackageSyncException(PackageSyncError.NETWORK_UNAVAILABLE)
                else -> {
                    partFile.delete()
                    throw PackageSyncException(PackageSyncError.INVALID_DATA)
                }
            }
        }
    }

    private fun streamResponse(
        response: Response,
        destination: File,
        append: Boolean,
        startingSize: Long,
        expectedSize: Long,
    ) {
        response.body.byteStream().use { input ->
            FileOutputStream(destination, append).use { output ->
                val buffer = ByteArray(DEFAULT_BUFFER_SIZE)
                var total = startingSize
                while (true) {
                    val read = input.read(buffer)
                    if (read == -1) break
                    total += read
                    if (total > expectedSize) {
                        throw PackageSyncException(PackageSyncError.INVALID_DATA)
                    }
                    output.write(buffer, 0, read)
                }
                output.fd.sync()
            }
        }
    }

    private fun validatePartialResponse(
        response: Response,
        expectedStart: Long,
        expectedTotal: Long,
    ) {
        val contentRange = response.header("Content-Range")
            ?: throw PackageSyncException(PackageSyncError.INVALID_DATA)
        val match = CONTENT_RANGE.matchEntire(contentRange)
            ?: throw PackageSyncException(PackageSyncError.INVALID_DATA)
        val start = match.groupValues[1].toLongOrNull()
        val end = match.groupValues[2].toLongOrNull()
        val total = match.groupValues[3].toLongOrNull()
        if (
            start != expectedStart ||
            end == null ||
            total != expectedTotal ||
            end < expectedStart ||
            end >= expectedTotal
        ) {
            throw PackageSyncException(PackageSyncError.INVALID_DATA)
        }
        val declaredLength = response.body.contentLength()
        if (declaredLength >= 0 && declaredLength != end - expectedStart + 1) {
            throw PackageSyncException(PackageSyncError.INVALID_DATA)
        }
    }

    private fun classifyManifestResponse(response: Response) {
        when {
            response.isSuccessful -> Unit
            response.code in RETRYABLE_CODES || response.code in 500..599 ->
                throw PackageSyncException(PackageSyncError.TEMPORARY_SERVER_FAILURE)
            else -> throw PackageSyncException(PackageSyncError.INVALID_MANIFEST)
        }
    }

    private fun classifyDataResponse(response: Response) {
        when {
            response.code == 200 || response.code == 206 -> Unit
            response.code in RETRYABLE_CODES || response.code in 500..599 ->
                throw PackageSyncException(PackageSyncError.TEMPORARY_SERVER_FAILURE)
            else -> throw PackageSyncException(PackageSyncError.INVALID_DATA)
        }
    }

    private suspend fun <T> execute(
        request: Request,
        block: (Response) -> T,
    ): T = withContext(Dispatchers.IO) {
        val call: Call = client.newCall(request)
        val cancellationHandle = coroutineContext.job.invokeOnCompletion { call.cancel() }
        try {
            coroutineContext.ensureActive()
            call.execute().use(block)
        } catch (exception: PackageSyncException) {
            throw exception
        } catch (exception: IOException) {
            throw PackageSyncException(PackageSyncError.NETWORK_UNAVAILABLE, exception)
        } finally {
            cancellationHandle.dispose()
        }
    }

    private companion object {
        val RETRYABLE_CODES = setOf(408, 425, 429)
        val CONTENT_RANGE = Regex("^bytes ([0-9]+)-([0-9]+)/([0-9]+)$")
    }
}

class PackageChecksumVerifier @Inject constructor() {
    fun verify(file: File, manifest: ValidatedPackageManifest): Boolean {
        if (file.length() != manifest.document.byteSize) return false
        val digest = MessageDigest.getInstance("SHA-256")
        file.inputStream().use { input ->
            val buffer = ByteArray(DEFAULT_BUFFER_SIZE)
            while (true) {
                val read = input.read(buffer)
                if (read == -1) break
                digest.update(buffer, 0, read)
            }
        }
        val expected = manifest.document.sha256.hexToByteArrayOrNull() ?: return false
        return MessageDigest.isEqual(digest.digest(), expected)
    }

    private fun String.hexToByteArrayOrNull(): ByteArray? {
        if (length != 64 || any { it !in '0'..'9' && it !in 'a'..'f' }) return null
        return ByteArray(length / 2) { index ->
            substring(index * 2, index * 2 + 2).toInt(16).toByte()
        }
    }
}
