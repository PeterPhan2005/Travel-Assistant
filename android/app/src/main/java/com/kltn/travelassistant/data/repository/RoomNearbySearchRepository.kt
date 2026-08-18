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
import com.kltn.travelassistant.feature.preferences.domain.PreferenceRepository
import com.kltn.travelassistant.feature.preferences.domain.documentOrNull
import com.kltn.travelassistant.feature.preferences.domain.toTravelPreferenceProfileOrNull
import javax.inject.Inject
import javax.inject.Singleton
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

@Singleton
class RoomNearbySearchRepository @Inject constructor(
    private val poiContentDao: PoiContentDao,
    private val preferenceRepository: PreferenceRepository,
) : NearbySearchRepository {
    constructor(poiContentDao: PoiContentDao) : this(
        poiContentDao = poiContentDao,
        preferenceRepository = NoPersonalizationPreferenceRepository,
    )

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
            val profile = preferenceRepository.state.value
                .documentOrNull()
                ?.toTravelPreferenceProfileOrNull()
            val rankedPois = NearbyPoiRanking.sort(nearbyPois, profile)
            NearbySearchResult.Success(rankedPois)
        } catch (exception: CancellationException) {
            throw exception
        } catch (_: Exception) {
            NearbySearchResult.DatabaseError
        }
    }

    private object NoPersonalizationPreferenceRepository : PreferenceRepository {
        override val state = kotlinx.coroutines.flow.MutableStateFlow(
            com.kltn.travelassistant.feature.preferences.domain.PreferenceSyncState.SignedOut,
        )

        override suspend fun updateLocal(
            document: com.kltn.travelassistant.feature.preferences.domain.PreferenceDocument,
        ) = com.kltn.travelassistant.feature.preferences.domain.PreferenceUpdateResult.SignedOut

        override fun refresh() = Unit

        override fun retry() = Unit
    }

    companion object {
        const val HO_CHI_MINH_CITY = "Ho Chi Minh City"
    }
}
