package com.kltn.travelassistant.data.seed

import kotlinx.serialization.Serializable

@Serializable
data class SeedDocument(
    val formatVersion: Int,
    val packageMetadata: SeedPackageMetadata,
    val pois: List<SeedPoi>,
    val aliases: List<SeedPoiAlias> = emptyList(),
    val menuItems: List<SeedMenuItem> = emptyList(),
    val narrations: List<SeedNarration> = emptyList(),
    val cultureItems: List<SeedCultureItem> = emptyList(),
)

@Serializable
data class SeedPackageMetadata(
    val packageId: String,
    val city: String,
    val version: String,
    val publishedAtEpochMillis: Long,
    val manifest: SeedManifest,
)

@Serializable
data class SeedManifest(
    val formatVersion: Int,
    val poiIds: List<String>,
)

@Serializable
data class SeedPoi(
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
data class SeedPoiAlias(
    val aliasId: String,
    val poiId: String,
    val alias: String,
    val normalizedAlias: String,
    val languageCode: String? = null,
)

@Serializable
data class SeedMenuItem(
    val menuItemId: String,
    val poiId: String,
    val dishName: String,
    val priceMinorUnits: Long,
    val currencyCode: String,
    val sourceType: String,
    val updatedAtEpochMillis: Long,
)

@Serializable
data class SeedNarration(
    val narrationId: String,
    val poiId: String,
    val languageCode: String,
    val content: String,
    val verificationStatus: String,
    val generatedAtEpochMillis: Long,
)

@Serializable
data class SeedCultureItem(
    val cultureItemId: String,
    val city: String,
    val area: String? = null,
    val topic: String,
    val content: String,
    val verificationStatus: String,
)
