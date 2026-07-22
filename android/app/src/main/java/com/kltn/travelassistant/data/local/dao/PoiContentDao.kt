package com.kltn.travelassistant.data.local.dao

import androidx.room.Dao
import androidx.room.Query
import androidx.room.Upsert
import com.kltn.travelassistant.data.local.entity.LocalCultureEntity
import com.kltn.travelassistant.data.local.entity.LocalMenuItemEntity
import com.kltn.travelassistant.data.local.entity.LocalNarrationEntity
import com.kltn.travelassistant.data.local.entity.LocalPoiAliasEntity
import com.kltn.travelassistant.data.local.entity.LocalPoiEntity

@Dao
interface PoiContentDao {
    @Upsert
    suspend fun upsertPois(pois: List<LocalPoiEntity>)

    @Upsert
    suspend fun upsertAliases(aliases: List<LocalPoiAliasEntity>)

    @Upsert
    suspend fun upsertMenuItems(menuItems: List<LocalMenuItemEntity>)

    @Upsert
    suspend fun upsertNarrations(narrations: List<LocalNarrationEntity>)

    @Upsert
    suspend fun upsertCultureItems(cultureItems: List<LocalCultureEntity>)

    @Query("SELECT * FROM local_pois WHERE poi_id = :poiId LIMIT 1")
    suspend fun getPoiById(poiId: String): LocalPoiEntity?

    @Query("SELECT * FROM local_pois WHERE city = :city ORDER BY name, poi_id")
    suspend fun getPoisByCity(city: String): List<LocalPoiEntity>

    @Query("SELECT * FROM local_poi_aliases WHERE poi_id = :poiId ORDER BY alias, alias_id")
    suspend fun getAliasesForPoi(poiId: String): List<LocalPoiAliasEntity>

    @Query(
        """
        SELECT * FROM local_poi_aliases
        WHERE poi_id IN (:poiIds)
        ORDER BY poi_id, alias, alias_id
        """,
    )
    suspend fun getAliasesForPois(poiIds: List<String>): List<LocalPoiAliasEntity>

    @Query("SELECT * FROM local_menu_items WHERE poi_id = :poiId ORDER BY dish_name, menu_item_id")
    suspend fun getMenuItemsForPoi(poiId: String): List<LocalMenuItemEntity>

    @Query(
        """
        SELECT * FROM local_narrations
        WHERE poi_id = :poiId AND language_code = :languageCode
        LIMIT 1
        """,
    )
    suspend fun getNarration(poiId: String, languageCode: String): LocalNarrationEntity?

    @Query("SELECT * FROM local_culture_items WHERE city = :city ORDER BY topic, culture_item_id")
    suspend fun getCultureByCity(city: String): List<LocalCultureEntity>

    @Query("SELECT * FROM local_culture_items WHERE area = :area ORDER BY topic, culture_item_id")
    suspend fun getCultureByArea(area: String): List<LocalCultureEntity>

    @Query("DELETE FROM local_pois WHERE poi_id = :poiId")
    suspend fun deletePoi(poiId: String): Int
}
