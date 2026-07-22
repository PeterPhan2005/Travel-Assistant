package com.kltn.travelassistant.data.repository

import com.kltn.travelassistant.data.local.dao.PoiContentDao
import com.kltn.travelassistant.feature.nearby.domain.GeographicCoordinate
import com.kltn.travelassistant.feature.nearby.domain.GeographicDistance
import com.kltn.travelassistant.feature.nearby.domain.NearbyPoi
import com.kltn.travelassistant.feature.nearby.domain.NearbyPoiRanking
import com.kltn.travelassistant.feature.nearby.domain.NearbySearchRepository
import com.kltn.travelassistant.feature.nearby.domain.NearbySearchResult
import com.kltn.travelassistant.feature.nearby.domain.PoiCategoryLabels
import com.kltn.travelassistant.feature.nearby.domain.VietnameseTextNormalizer
import javax.inject.Inject
import javax.inject.Singleton
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

@Singleton
class RoomNearbySearchRepository @Inject constructor(
    private val poiContentDao: PoiContentDao,
) : NearbySearchRepository {
    override suspend fun search(
        latitude: Double,
        longitude: Double,
        query: String,
    ): NearbySearchResult = withContext(Dispatchers.Default) {
        val origin = GeographicCoordinate(latitude, longitude)
        if (!origin.isValid) return@withContext NearbySearchResult.InvalidLocation

        try {
            val pois = poiContentDao.getPoisByCity(HO_CHI_MINH_CITY)
            val aliasesByPoiId = if (pois.isEmpty()) {
                emptyMap()
            } else {
                poiContentDao.getAliasesForPois(pois.map { poi -> poi.poiId })
                    .groupBy { alias -> alias.poiId }
            }
            val normalizedQuery = VietnameseTextNormalizer.normalize(query)
            val nearbyPois = pois.mapNotNull { poi ->
                val categoryLabel = PoiCategoryLabels.labelFor(poi.category)
                val searchableValues = buildList {
                    add(poi.name)
                    add(poi.category)
                    add(PoiCategoryLabels.searchTextFor(categoryLabel))
                    aliasesByPoiId[poi.poiId].orEmpty().forEach { alias ->
                        add(alias.alias)
                        add(alias.normalizedAlias)
                    }
                }
                if (normalizedQuery.isNotEmpty() && searchableValues.none { value ->
                        VietnameseTextNormalizer.normalize(value).contains(normalizedQuery)
                    }
                ) {
                    return@mapNotNull null
                }

                val distance = GeographicDistance.metresBetween(
                    origin = origin,
                    destination = GeographicCoordinate(poi.latitude, poi.longitude),
                ) ?: return@mapNotNull null
                NearbyPoi(
                    poiId = poi.poiId,
                    displayName = poi.name,
                    category = poi.category,
                    categoryLabel = categoryLabel,
                    distanceMeters = distance,
                )
            }
            val rankedPois = NearbyPoiRanking.sort(nearbyPois)
            NearbySearchResult.Success(rankedPois)
        } catch (exception: CancellationException) {
            throw exception
        } catch (_: Exception) {
            NearbySearchResult.DatabaseError
        }
    }

    companion object {
        const val HO_CHI_MINH_CITY = "Ho Chi Minh City"
    }
}
