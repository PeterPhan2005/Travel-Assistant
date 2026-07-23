package com.kltn.travelassistant.data.repository

import com.kltn.travelassistant.data.local.dao.PoiContentDao
import com.kltn.travelassistant.feature.nearby.domain.PoiCategoryLabels
import com.kltn.travelassistant.feature.poi.domain.PoiDetail
import com.kltn.travelassistant.feature.poi.domain.PoiDetailRepository
import com.kltn.travelassistant.feature.poi.domain.PoiDetailResult
import com.kltn.travelassistant.feature.poi.domain.PoiMenuItem
import com.kltn.travelassistant.feature.poi.domain.PoiNarration
import com.kltn.travelassistant.feature.poi.domain.PoiNavigationTarget
import javax.inject.Inject
import javax.inject.Singleton
import kotlinx.coroutines.CancellationException

@Singleton
class RoomPoiDetailRepository @Inject constructor(
    private val poiContentDao: PoiContentDao,
) : PoiDetailRepository {
    override suspend fun getPoiDetail(
        poiId: String,
        languageCode: String,
    ): PoiDetailResult = try {
        val snapshot = poiContentDao.getPoiDetailSnapshot(poiId, languageCode)
            ?: return PoiDetailResult.NotFound
        val narration = snapshot.narration
            ?.takeIf { storedNarration -> storedNarration.content.isNotBlank() }
            ?.let { storedNarration ->
                storedNarration.sourceLabel
                    ?.trim()
                    ?.takeIf(String::isNotEmpty)
                    ?.let { sourceLabel ->
                        PoiNarration(
                            content = storedNarration.content,
                            sourceLabel = sourceLabel,
                        )
                    }
            }
        PoiDetailResult.Success(
            PoiDetail(
                poiId = snapshot.poi.poiId,
                name = snapshot.poi.name,
                category = PoiCategoryLabels.labelFor(snapshot.poi.category),
                city = snapshot.poi.city,
                area = snapshot.poi.area.nonBlankOrNull(),
                address = snapshot.poi.address.nonBlankOrNull(),
                shortDescription = snapshot.poi.shortDescription.nonBlankOrNull(),
                menuItems = snapshot.menuItems.map { item ->
                    PoiMenuItem(
                        dishName = item.dishName,
                        priceMinorUnits = item.priceMinorUnits,
                        currencyCode = item.currencyCode,
                        sourceType = item.sourceType,
                        updatedAtEpochMillis = item.updatedAtEpochMillis,
                    )
                }.toList(),
                narration = narration,
                navigationTarget = PoiNavigationTarget(
                    poiId = snapshot.poi.poiId,
                    displayName = snapshot.poi.name,
                    latitude = snapshot.poi.latitude,
                    longitude = snapshot.poi.longitude,
                ),
            ),
        )
    } catch (exception: CancellationException) {
        throw exception
    } catch (_: Exception) {
        PoiDetailResult.DatabaseError
    }

    private fun String?.nonBlankOrNull(): String? = this?.takeIf(String::isNotBlank)
}
