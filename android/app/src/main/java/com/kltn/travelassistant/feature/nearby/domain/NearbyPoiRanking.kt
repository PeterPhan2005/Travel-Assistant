package com.kltn.travelassistant.feature.nearby.domain

import com.kltn.travelassistant.feature.preferences.domain.TravelInterest
import com.kltn.travelassistant.feature.preferences.domain.TravelPreferenceProfile

object NearbyPoiRanking {
    fun sort(
        pois: List<NearbyPoi>,
        profile: TravelPreferenceProfile? = null,
    ): List<NearbyPoi> = pois.sortedWith(
        compareBy<NearbyPoi> { poi -> interestBucket(poi, profile) }
            .thenBy { poi -> poi.distanceMeters }
            .thenBy { poi -> VietnameseTextNormalizer.normalize(poi.displayName) }
            .thenBy { poi -> poi.poiId },
    )

    private fun interestBucket(
        poi: NearbyPoi,
        profile: TravelPreferenceProfile?,
    ): Int {
        val selected = profile?.interests.orEmpty()
        if (selected.isEmpty()) return 0
        return if (categoryInterest(poi.category) in selected) 0 else 1
    }

    private fun categoryInterest(category: String): TravelInterest? {
        val tokens = VietnameseTextNormalizer.normalize(category)
            .lowercase()
            .split(Regex("[^a-z0-9]+"))
            .filter(String::isNotEmpty)
            .toSet()
        return CATEGORY_INTERESTS.entries.firstOrNull { (_, keywords) ->
            tokens.any(keywords::contains)
        }?.key
    }

    private val CATEGORY_INTERESTS = linkedMapOf(
        TravelInterest.FOOD_AND_CAFES to setOf("bakery", "cafe", "coffee", "food", "restaurant"),
        TravelInterest.CULTURE_AND_HISTORY to setOf(
            "art", "church", "culture", "gallery", "heritage", "historic", "history",
            "museum", "pagoda", "temple",
        ),
        TravelInterest.SCENIC_AND_LANDMARKS to setOf(
            "attraction", "landmark", "monument", "scenic", "viewpoint",
        ),
        TravelInterest.NATURE_AND_OUTDOORS to setOf(
            "beach", "garden", "hiking", "nature", "outdoor", "park",
        ),
        TravelInterest.LOCAL_LIFE_AND_MARKETS to setOf(
            "local", "market", "neighborhood", "shopping", "street",
        ),
        TravelInterest.ENTERTAINMENT_AND_NIGHTLIFE to setOf(
            "bar", "cinema", "club", "entertainment", "nightlife", "theater",
        ),
        TravelInterest.FAMILY_ACTIVITIES to setOf(
            "amusement", "aquarium", "family", "playground", "theme", "zoo",
        ),
        TravelInterest.WELLNESS_AND_RELAXATION to setOf(
            "massage", "relaxation", "spa", "wellness", "yoga",
        ),
    )
}
