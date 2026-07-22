package com.kltn.travelassistant.feature.nearby.domain

object NearbyPoiRanking {
    fun sort(pois: List<NearbyPoi>): List<NearbyPoi> = pois.sortedWith(
        compareBy<NearbyPoi> { poi -> poi.distanceMeters }
            .thenBy { poi -> VietnameseTextNormalizer.normalize(poi.displayName) }
            .thenBy { poi -> poi.poiId },
    )
}
