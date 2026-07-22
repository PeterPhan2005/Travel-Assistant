package com.kltn.travelassistant.feature.nearby.domain

data class NearbyPoi(
    val poiId: String,
    val displayName: String,
    val category: String,
    val categoryLabel: PoiCategoryLabel,
    val distanceMeters: Double,
)

sealed interface NearbySearchResult {
    data class Success(val pois: List<NearbyPoi>) : NearbySearchResult

    data object InvalidLocation : NearbySearchResult

    data object DatabaseError : NearbySearchResult
}

interface NearbySearchRepository {
    suspend fun search(
        latitude: Double,
        longitude: Double,
        query: String,
    ): NearbySearchResult
}
