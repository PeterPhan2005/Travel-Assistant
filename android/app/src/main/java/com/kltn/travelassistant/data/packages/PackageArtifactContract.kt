package com.kltn.travelassistant.data.packages

import com.kltn.travelassistant.data.local.entity.LocalMenuItemEntity
import com.kltn.travelassistant.data.local.entity.LocalNarrationEntity
import com.kltn.travelassistant.data.local.entity.LocalPoiAliasEntity
import com.kltn.travelassistant.data.local.entity.LocalPoiEntity
import com.kltn.travelassistant.data.local.entity.TravelPackageEntity
import java.io.File
import java.nio.charset.CodingErrorAction
import java.nio.charset.StandardCharsets
import javax.inject.Inject
import kotlinx.serialization.Serializable
import kotlinx.serialization.SerializationException
import kotlinx.serialization.json.Json

@Serializable
data class PackageArtifactDocument(
    val formatVersion: Int,
    val packageMetadata: PackageArtifactMetadata,
    val pois: List<PackageArtifactPoi> = emptyList(),
    val aliases: List<PackageArtifactAlias> = emptyList(),
    val menuItems: List<PackageArtifactMenuItem> = emptyList(),
    val narrations: List<PackageArtifactNarration> = emptyList(),
)

@Serializable
data class PackageArtifactMetadata(
    val packageId: String,
    val city: String,
    val version: String,
    val publishedAtEpochMillis: Long,
    val manifest: PackageArtifactPoiManifest,
)

@Serializable
data class PackageArtifactPoiManifest(
    val formatVersion: Int,
    val poiIds: List<String>,
)

@Serializable
data class PackageArtifactPoi(
    val poiId: String,
    val name: String,
    val city: String,
    val area: String? = null,
    val category: String,
    val latitude: Double,
    val longitude: Double,
    val address: String? = null,
    val shortDescription: String? = null,
    val status: String,
    val updatedAtEpochMillis: Long,
)

@Serializable
data class PackageArtifactAlias(
    val aliasId: String,
    val poiId: String,
    val alias: String,
    val normalizedAlias: String,
    val languageCode: String? = null,
)

@Serializable
data class PackageArtifactMenuItem(
    val menuItemId: String,
    val poiId: String,
    val dishName: String,
    val priceMinorUnits: Long,
    val currencyCode: String,
    val sourceType: String,
    val updatedAtEpochMillis: Long,
)

@Serializable
data class PackageArtifactNarration(
    val narrationId: String,
    val poiId: String,
    val languageCode: String,
    val content: String,
    val verificationStatus: String,
    val generatedAtEpochMillis: Long,
    val sourceLabel: String,
)

data class ValidatedTravelPackage(
    val metadata: TravelPackageEntity,
    val pois: List<LocalPoiEntity>,
    val aliases: List<LocalPoiAliasEntity>,
    val menuItems: List<LocalMenuItemEntity>,
    val narrations: List<LocalNarrationEntity>,
)

class PackageArtifactParser @Inject constructor() {
    private val json = Json {
        ignoreUnknownKeys = false
        isLenient = false
        coerceInputValues = false
        allowSpecialFloatingPointValues = false
        useAlternativeNames = false
        explicitNulls = true
    }

    fun parse(file: File): PackageArtifactDocument {
        val bytes = try {
            file.readBytes()
        } catch (exception: Exception) {
            throw PackageSyncException(PackageSyncError.INVALID_DATA, exception)
        }
        val rawJson = try {
            StandardCharsets.UTF_8.newDecoder()
                .onMalformedInput(CodingErrorAction.REPORT)
                .onUnmappableCharacter(CodingErrorAction.REPORT)
                .decode(java.nio.ByteBuffer.wrap(bytes))
                .toString()
        } catch (exception: Exception) {
            throw PackageSyncException(PackageSyncError.INVALID_DATA, exception)
        }
        return try {
            json.decodeFromString(rawJson)
        } catch (exception: SerializationException) {
            throw PackageSyncException(PackageSyncError.INVALID_DATA, exception)
        } catch (exception: IllegalArgumentException) {
            throw PackageSyncException(PackageSyncError.INVALID_DATA, exception)
        }
    }
}

class PackageArtifactValidator @Inject constructor() {
    fun validate(
        artifact: PackageArtifactDocument,
        manifest: ValidatedPackageManifest,
    ): ValidatedTravelPackage {
        invalidUnless(artifact.formatVersion == manifest.document.artifactSchemaVersion)
        val metadata = artifact.packageMetadata
        invalidUnless(metadata.manifest.formatVersion == artifact.formatVersion)
        invalidUnless(metadata.packageId == manifest.document.packageId)
        invalidUnless(metadata.city == manifestCityName(manifest))
        invalidUnless(metadata.version == manifest.document.contentVersion)
        invalidUnless(metadata.publishedAtEpochMillis == manifest.publishedAtEpochMillis)
        validateStableId(metadata.packageId)
        validateText(metadata.city, 100)
        invalidUnless(CONTENT_VERSION.matches(metadata.version))

        val poiIds = artifact.pois.map(PackageArtifactPoi::poiId)
        invalidUnless(poiIds == poiIds.sorted())
        invalidUnless(poiIds.size == poiIds.toSet().size)
        invalidUnless(metadata.manifest.poiIds == poiIds)
        val knownPoiIds = poiIds.toSet()

        artifact.pois.forEach { poi ->
            validateStableId(poi.poiId, HCMC_ID_PREFIX)
            validateText(poi.name, 200)
            invalidUnless(poi.city == metadata.city)
            validateOptionalText(poi.area, 100)
            validateText(poi.category, 80)
            invalidUnless(poi.latitude.isFinite() && poi.latitude in -90.0..90.0)
            invalidUnless(poi.longitude.isFinite() && poi.longitude in -180.0..180.0)
            validateOptionalText(poi.address, 500)
            validateOptionalText(poi.shortDescription, 2_000)
            invalidUnless(poi.status == "curated")
            invalidUnless(poi.updatedAtEpochMillis > 0)
        }
        validateChildren(artifact, knownPoiIds)

        return ValidatedTravelPackage(
            metadata = TravelPackageEntity(
                packageId = metadata.packageId,
                city = metadata.city,
                version = metadata.version,
                manifestJson = manifest.rawJson,
                publishedAtEpochMillis = metadata.publishedAtEpochMillis,
            ),
            pois = artifact.pois.map { poi ->
                LocalPoiEntity(
                    poiId = poi.poiId,
                    name = poi.name,
                    city = poi.city,
                    area = poi.area,
                    category = poi.category,
                    latitude = poi.latitude,
                    longitude = poi.longitude,
                    address = poi.address,
                    shortDescription = poi.shortDescription,
                    status = poi.status,
                    updatedAtEpochMillis = poi.updatedAtEpochMillis,
                )
            },
            aliases = artifact.aliases.map { alias ->
                LocalPoiAliasEntity(
                    aliasId = alias.aliasId,
                    poiId = alias.poiId,
                    alias = alias.alias,
                    normalizedAlias = alias.normalizedAlias,
                    languageCode = alias.languageCode,
                )
            },
            menuItems = artifact.menuItems.map { item ->
                LocalMenuItemEntity(
                    menuItemId = item.menuItemId,
                    poiId = item.poiId,
                    dishName = item.dishName,
                    priceMinorUnits = item.priceMinorUnits,
                    currencyCode = item.currencyCode,
                    sourceType = item.sourceType,
                    updatedAtEpochMillis = item.updatedAtEpochMillis,
                )
            },
            narrations = artifact.narrations.map { narration ->
                LocalNarrationEntity(
                    narrationId = narration.narrationId,
                    poiId = narration.poiId,
                    languageCode = narration.languageCode,
                    content = narration.content,
                    verificationStatus = narration.verificationStatus,
                    generatedAtEpochMillis = narration.generatedAtEpochMillis,
                    sourceLabel = narration.sourceLabel,
                )
            },
        )
    }

    private fun validateChildren(
        artifact: PackageArtifactDocument,
        knownPoiIds: Set<String>,
    ) {
        validateSortedUnique(artifact.aliases.map(PackageArtifactAlias::aliasId))
        artifact.aliases.forEach { alias ->
            validateStableId(alias.aliasId, HCMC_ID_PREFIX)
            invalidUnless(alias.poiId in knownPoiIds)
            validateText(alias.alias, 200)
            validateText(alias.normalizedAlias, 200)
            alias.languageCode?.let(::validateLanguage)
        }

        validateSortedUnique(artifact.menuItems.map(PackageArtifactMenuItem::menuItemId))
        artifact.menuItems.forEach { item ->
            validateStableId(item.menuItemId, HCMC_ID_PREFIX)
            invalidUnless(item.poiId in knownPoiIds)
            validateText(item.dishName, 200)
            invalidUnless(item.priceMinorUnits >= 0)
            invalidUnless(CURRENCY.matches(item.currencyCode))
            invalidUnless(item.sourceType in SOURCE_TYPES)
            invalidUnless(item.updatedAtEpochMillis > 0)
        }

        validateSortedUnique(artifact.narrations.map(PackageArtifactNarration::narrationId))
        invalidUnless(
            artifact.narrations.map { it.poiId to it.languageCode }.let {
                it.size == it.toSet().size
            },
        )
        artifact.narrations.forEach { narration ->
            validateStableId(narration.narrationId, HCMC_ID_PREFIX)
            invalidUnless(narration.poiId in knownPoiIds)
            validateLanguage(narration.languageCode)
            validateText(narration.content, 4_000, minimum = 20)
            invalidUnless(narration.verificationStatus in VERIFICATION_STATUSES)
            invalidUnless(narration.generatedAtEpochMillis > 0)
            validateText(narration.sourceLabel, 200)
        }
    }

    private fun validateSortedUnique(values: List<String>) {
        invalidUnless(values == values.sorted())
        invalidUnless(values.size == values.toSet().size)
    }

    private fun validateStableId(value: String, requiredPrefix: String? = null) {
        invalidUnless(value.length <= 120 && STABLE_ID.matches(value))
        requiredPrefix?.let { invalidUnless(value.startsWith(it)) }
    }

    private fun validateLanguage(value: String) {
        invalidUnless(value.length <= 16 && LANGUAGE.matches(value))
    }

    private fun validateOptionalText(value: String?, maximum: Int) {
        value?.let { validateText(it, maximum) }
    }

    private fun validateText(value: String, maximum: Int, minimum: Int = 1) {
        invalidUnless(
            value.length in minimum..maximum &&
                value.isNotBlank() &&
                value == value.trim(),
        )
    }

    private fun manifestCityName(manifest: ValidatedPackageManifest): String =
        when (manifest.document.city) {
            "hcmc" -> "Ho Chi Minh City"
            else -> throw PackageSyncException(PackageSyncError.UNSUPPORTED_PACKAGE)
        }

    private fun invalidUnless(condition: Boolean) {
        if (!condition) throw PackageSyncException(PackageSyncError.INVALID_DATA)
    }

    private companion object {
        const val HCMC_ID_PREFIX = "hcmc-"
        val STABLE_ID = Regex("^[a-z0-9]+(?:-[a-z0-9]+)*$")
        val CONTENT_VERSION = Regex("^[0-9]+(?:\\.[0-9]+){0,2}$")
        val CURRENCY = Regex("^[A-Z]{3}$")
        val LANGUAGE = Regex("^[a-z]{2,3}(?:-[A-Z]{2})?$")
        val SOURCE_TYPES = setOf(
            "official_government",
            "official_institution",
            "official_operator",
            "official_tourism",
        )
        val VERIFICATION_STATUSES = setOf("verified", "fallback")
    }
}
