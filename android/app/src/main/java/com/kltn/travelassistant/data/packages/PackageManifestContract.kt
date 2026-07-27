package com.kltn.travelassistant.data.packages

import com.kltn.travelassistant.BuildConfig
import com.kltn.travelassistant.feature.downloads.domain.PackageCity
import java.time.Instant
import javax.inject.Inject
import javax.inject.Singleton
import kotlinx.serialization.Serializable
import kotlinx.serialization.SerializationException
import kotlinx.serialization.json.Json
import okhttp3.HttpUrl
import okhttp3.HttpUrl.Companion.toHttpUrlOrNull

@Serializable
data class PackageManifestDocument(
    val schemaVersion: Int,
    val artifactSchemaVersion: Int,
    val packageId: String,
    val city: String,
    val contentVersion: String,
    val publishedAt: String,
    val dataFilename: String,
    val mediaType: String,
    val byteSize: Long,
    val sha256: String,
)

data class PackageManifestLocation(
    val city: PackageCity,
    val manifestUrl: HttpUrl,
    val allowCleartext: Boolean = false,
)

fun interface PackageManifestLocationProvider {
    fun locationFor(city: PackageCity): PackageManifestLocation?
}

@Singleton
class BuildConfigPackageManifestLocationProvider @Inject constructor() :
    PackageManifestLocationProvider {
    override fun locationFor(city: PackageCity): PackageManifestLocation? {
        if (city != PackageCity.HCMC) return null
        val url = BuildConfig.HCMC_PACKAGE_MANIFEST_URL.toHttpUrlOrNull() ?: return null
        val isApprovedDebugCleartext = BuildConfig.DEBUG &&
            url.scheme == "http" &&
            url.host == DEBUG_EMULATOR_HOST &&
            url.port == DEBUG_SERVER_PORT
        if (url.scheme != "https" && !isApprovedDebugCleartext) return null
        return PackageManifestLocation(
            city = city,
            manifestUrl = url,
            allowCleartext = isApprovedDebugCleartext,
        )
    }

    private companion object {
        const val DEBUG_EMULATOR_HOST = "10.0.2.2"
        const val DEBUG_SERVER_PORT = 8081
    }
}

data class ValidatedPackageManifest(
    val document: PackageManifestDocument,
    val publishedAtEpochMillis: Long,
    val dataUrl: HttpUrl,
    val rawJson: String,
)

class PackageManifestParser @Inject constructor() {
    private val json = Json {
        ignoreUnknownKeys = false
        isLenient = false
        coerceInputValues = false
        allowSpecialFloatingPointValues = false
        useAlternativeNames = false
        explicitNulls = true
    }

    fun parse(rawJson: String): PackageManifestDocument = try {
        json.decodeFromString(rawJson)
    } catch (exception: SerializationException) {
        throw PackageSyncException(PackageSyncError.INVALID_MANIFEST, exception)
    } catch (exception: IllegalArgumentException) {
        throw PackageSyncException(PackageSyncError.INVALID_MANIFEST, exception)
    }
}

class PackageManifestValidator @Inject constructor() {
    fun validate(
        document: PackageManifestDocument,
        rawJson: String,
        location: PackageManifestLocation,
    ): ValidatedPackageManifest {
        invalidUnless(document.schemaVersion == SUPPORTED_SCHEMA_VERSION)
        invalidUnless(document.artifactSchemaVersion == SUPPORTED_ARTIFACT_SCHEMA_VERSION)
        unsupportedUnless(document.city == location.city.code)
        unsupportedUnless(document.packageId == location.city.packageId)
        invalidUnless(STABLE_ID.matches(document.packageId))
        invalidUnless(CONTENT_VERSION.matches(document.contentVersion))
        invalidUnless(PUBLISHED_AT.matches(document.publishedAt))
        invalidUnless(document.mediaType == JSON_MEDIA_TYPE)
        invalidUnless(document.byteSize in 1..MAX_ARTIFACT_BYTES)
        invalidUnless(SHA256.matches(document.sha256))
        invalidUnless(SAFE_DATA_FILENAME.matches(document.dataFilename))
        invalidUnless(isSafeRelativeFilename(document.dataFilename))
        validateManifestScheme(location)

        val publishedAtEpochMillis = try {
            Instant.parse(document.publishedAt).toEpochMilli()
        } catch (exception: Exception) {
            throw PackageSyncException(PackageSyncError.INVALID_MANIFEST, exception)
        }
        invalidUnless(publishedAtEpochMillis > 0)

        val dataUrl = location.manifestUrl.resolve(document.dataFilename)
            ?: throw PackageSyncException(PackageSyncError.INVALID_MANIFEST)
        invalidUnless(
            dataUrl.scheme == location.manifestUrl.scheme &&
                dataUrl.host == location.manifestUrl.host &&
                dataUrl.port == location.manifestUrl.port,
        )
        return ValidatedPackageManifest(
            document = document,
            publishedAtEpochMillis = publishedAtEpochMillis,
            dataUrl = dataUrl,
            rawJson = rawJson,
        )
    }

    private fun validateManifestScheme(location: PackageManifestLocation) {
        val url = location.manifestUrl
        val valid = url.scheme == "https" ||
            (url.scheme == "http" && location.allowCleartext)
        unsupportedUnless(valid)
    }

    private fun isSafeRelativeFilename(filename: String): Boolean =
        filename != "." &&
            filename != ".." &&
            !filename.contains('/') &&
            !filename.contains('\\') &&
            !filename.contains("..") &&
            !filename.startsWith('.') &&
            !filename.contains("://")

    private fun invalidUnless(condition: Boolean) {
        if (!condition) throw PackageSyncException(PackageSyncError.INVALID_MANIFEST)
    }

    private fun unsupportedUnless(condition: Boolean) {
        if (!condition) throw PackageSyncException(PackageSyncError.UNSUPPORTED_PACKAGE)
    }

    companion object {
        const val MAX_ARTIFACT_BYTES = 50L * 1024L * 1024L
        const val MAX_MANIFEST_BYTES = 64L * 1024L
        private const val SUPPORTED_SCHEMA_VERSION = 1
        private const val SUPPORTED_ARTIFACT_SCHEMA_VERSION = 1
        private const val JSON_MEDIA_TYPE = "application/json"
        private val STABLE_ID = Regex("^[a-z0-9]+(?:-[a-z0-9]+)*$")
        private val CONTENT_VERSION = Regex("^[0-9]+(?:\\.[0-9]+){0,2}$")
        private val PUBLISHED_AT = Regex(
            "^[0-9]{4}-[0-9]{2}-[0-9]{2}T" +
                "[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\\.[0-9]{1,6})?Z$",
        )
        private val SAFE_DATA_FILENAME = Regex(
            "^[a-z0-9]+(?:-[a-z0-9]+)*-[0-9]+(?:\\.[0-9]+){0,2}\\.data\\.json$",
        )
        private val SHA256 = Regex("^[0-9a-f]{64}$")
    }
}

enum class PackageSyncError(val retryable: Boolean) {
    NETWORK_UNAVAILABLE(true),
    TEMPORARY_SERVER_FAILURE(true),
    INVALID_MANIFEST(false),
    UNSUPPORTED_PACKAGE(false),
    CHECKSUM_MISMATCH(false),
    INVALID_DATA(false),
    ACTIVATION_FAILED(false),
}

class PackageSyncException(
    val error: PackageSyncError,
    cause: Throwable? = null,
) : Exception(error.name, cause)
