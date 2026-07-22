package com.kltn.travelassistant.data.seed

import com.kltn.travelassistant.data.local.entity.LocalCultureEntity
import com.kltn.travelassistant.data.local.entity.LocalMenuItemEntity
import com.kltn.travelassistant.data.local.entity.LocalNarrationEntity
import com.kltn.travelassistant.data.local.entity.LocalPoiAliasEntity
import com.kltn.travelassistant.data.local.entity.LocalPoiEntity
import com.kltn.travelassistant.data.local.entity.TravelPackageEntity
import javax.inject.Inject

class SeedValidator @Inject constructor(
    private val parser: SeedDocumentParser,
) {
    fun validate(document: SeedDocument): ValidatedSeed {
        requireValid(document.formatVersion == SUPPORTED_FORMAT_VERSION)
        validatePackage(document)
        validatePois(document.pois)
        validateAliases(document.aliases, document.pois)
        validateMenuItems(document.menuItems, document.pois)
        validateNarrations(document.narrations, document.pois)
        validateCultureItems(document.cultureItems)

        return document.toValidatedSeed()
    }

    private fun validatePackage(document: SeedDocument) {
        val metadata = document.packageMetadata
        requireNonBlank(metadata.packageId)
        requireValid(metadata.city == SUPPORTED_CITY)
        requireNonBlank(metadata.version)
        requireValid(metadata.publishedAtEpochMillis > 0)
        requireValid(metadata.manifest.formatVersion == document.formatVersion)
        requireUnique(metadata.manifest.poiIds)
        metadata.manifest.poiIds.forEach(::requireNonBlank)

        val poiIds = document.pois.map(SeedPoi::poiId)
        requireValid(metadata.manifest.poiIds.toSet() == poiIds.toSet())
    }

    private fun validatePois(pois: List<SeedPoi>) {
        requireValid(pois.size >= MINIMUM_POI_COUNT)
        requireUnique(pois.map(SeedPoi::poiId))
        pois.forEach { poi ->
            requireNonBlank(poi.poiId)
            requireNonBlank(poi.name)
            requireValid(poi.city == SUPPORTED_CITY)
            requireOptionalNonBlank(poi.area)
            requireNonBlank(poi.category)
            requireValid(poi.latitude.isFinite() && poi.latitude in -90.0..90.0)
            requireValid(poi.longitude.isFinite() && poi.longitude in -180.0..180.0)
            requireOptionalNonBlank(poi.address)
            requireOptionalNonBlank(poi.shortDescription)
            requireNonBlank(poi.status)
            requireValid(poi.updatedAtEpochMillis > 0)
        }
    }

    private fun validateAliases(aliases: List<SeedPoiAlias>, pois: List<SeedPoi>) {
        val poiIds = pois.mapTo(mutableSetOf(), SeedPoi::poiId)
        requireUnique(aliases.map(SeedPoiAlias::aliasId))
        aliases.forEach { alias ->
            requireNonBlank(alias.aliasId)
            requireValid(alias.poiId in poiIds)
            requireNonBlank(alias.alias)
            requireNonBlank(alias.normalizedAlias)
            requireOptionalNonBlank(alias.languageCode)
        }
    }

    private fun validateMenuItems(menuItems: List<SeedMenuItem>, pois: List<SeedPoi>) {
        val poiIds = pois.mapTo(mutableSetOf(), SeedPoi::poiId)
        requireUnique(menuItems.map(SeedMenuItem::menuItemId))
        menuItems.forEach { item ->
            requireNonBlank(item.menuItemId)
            requireValid(item.poiId in poiIds)
            requireNonBlank(item.dishName)
            requireValid(item.priceMinorUnits >= 0)
            requireNonBlank(item.currencyCode)
            requireNonBlank(item.sourceType)
            requireValid(item.updatedAtEpochMillis > 0)
        }
    }

    private fun validateNarrations(narrations: List<SeedNarration>, pois: List<SeedPoi>) {
        val poiIds = pois.mapTo(mutableSetOf(), SeedPoi::poiId)
        requireUnique(narrations.map(SeedNarration::narrationId))
        requireUnique(narrations.map { it.poiId to it.languageCode })
        narrations.forEach { narration ->
            requireNonBlank(narration.narrationId)
            requireValid(narration.poiId in poiIds)
            requireNonBlank(narration.languageCode)
            requireNonBlank(narration.content)
            requireNonBlank(narration.verificationStatus)
            requireValid(narration.generatedAtEpochMillis > 0)
            requireOptionalNonBlank(narration.sourceLabel)
        }
    }

    private fun validateCultureItems(cultureItems: List<SeedCultureItem>) {
        requireUnique(cultureItems.map(SeedCultureItem::cultureItemId))
        cultureItems.forEach { item ->
            requireNonBlank(item.cultureItemId)
            requireValid(item.city == SUPPORTED_CITY)
            requireOptionalNonBlank(item.area)
            requireNonBlank(item.topic)
            requireNonBlank(item.content)
            requireNonBlank(item.verificationStatus)
        }
    }

    private fun SeedDocument.toValidatedSeed() = ValidatedSeed(
        travelPackage = TravelPackageEntity(
            packageId = packageMetadata.packageId,
            city = packageMetadata.city,
            version = packageMetadata.version,
            manifestJson = parser.encodeManifest(packageMetadata.manifest),
            publishedAtEpochMillis = packageMetadata.publishedAtEpochMillis,
        ),
        pois = pois.map { poi ->
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
        aliases = aliases.map { alias ->
            LocalPoiAliasEntity(
                aliasId = alias.aliasId,
                poiId = alias.poiId,
                alias = alias.alias,
                normalizedAlias = alias.normalizedAlias,
                languageCode = alias.languageCode,
            )
        },
        menuItems = menuItems.map { item ->
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
        narrations = narrations.map { narration ->
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
        cultureItems = cultureItems.map { item ->
            LocalCultureEntity(
                cultureItemId = item.cultureItemId,
                city = item.city,
                area = item.area,
                topic = item.topic,
                content = item.content,
                verificationStatus = item.verificationStatus,
            )
        },
    )

    private fun requireNonBlank(value: String) = requireValid(value.isNotBlank())

    private fun requireOptionalNonBlank(value: String?) = requireValid(value == null || value.isNotBlank())

    private fun <T> requireUnique(values: List<T>) = requireValid(values.size == values.toSet().size)

    private fun requireValid(condition: Boolean) {
        if (!condition) throw SeedValidationException()
    }

    companion object {
        const val SUPPORTED_CITY = "Ho Chi Minh City"
        const val SUPPORTED_FORMAT_VERSION = 1
        const val MINIMUM_POI_COUNT = 5
    }
}

class SeedValidationException : IllegalArgumentException()
