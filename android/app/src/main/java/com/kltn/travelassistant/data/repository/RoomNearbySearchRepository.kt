package com.kltn.travelassistant.data.repository

import com.kltn.travelassistant.data.local.dao.PoiContentDao
import com.kltn.travelassistant.feature.nearby.domain.GeographicCoordinate
import com.kltn.travelassistant.feature.nearby.domain.GeographicDistance
import com.kltn.travelassistant.feature.nearby.domain.NearbyPoi
import com.kltn.travelassistant.feature.nearby.domain.NearbyPoiRanking
import com.kltn.travelassistant.feature.nearby.domain.NearbySearchRepository
import com.kltn.travelassistant.feature.nearby.domain.NearbySearchResult
import com.kltn.travelassistant.feature.nearby.domain.CompiledOfflineSearchQuery
import com.kltn.travelassistant.feature.nearby.domain.OfflineSearchQueryCompiler
import com.kltn.travelassistant.feature.nearby.domain.PoiCategoryLabels
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
            val pois = when (val compiledQuery = OfflineSearchQueryCompiler.compile(query)) {
                CompiledOfflineSearchQuery.Blank ->
                    poiContentDao.getActivePackagePoisByCity(HO_CHI_MINH_CITY)
                CompiledOfflineSearchQuery.NoSearchableTerms -> emptyList()
                is CompiledOfflineSearchQuery.Match -> poiContentDao.searchActivePackagePois(
                    city = HO_CHI_MINH_CITY,
                    matchExpression = compiledQuery.expression,
                )
            }
            val nearbyPois = pois.mapNotNull { poi ->
                val categoryLabel = PoiCategoryLabels.labelFor(poi.category)
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
