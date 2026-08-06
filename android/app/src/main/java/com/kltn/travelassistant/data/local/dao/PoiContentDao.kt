package com.kltn.travelassistant.data.local.dao

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.Query
import androidx.room.Transaction
import androidx.room.Upsert
import com.kltn.travelassistant.data.local.PoiSearchIndexBuilder
import com.kltn.travelassistant.data.local.entity.LocalCultureEntity
import com.kltn.travelassistant.data.local.entity.LocalMenuItemEntity
import com.kltn.travelassistant.data.local.entity.LocalNarrationEntity
import com.kltn.travelassistant.data.local.entity.LocalPoiAliasEntity
import com.kltn.travelassistant.data.local.entity.LocalPoiEntity
import com.kltn.travelassistant.data.local.entity.LocalPoiSearchFtsEntity
import com.kltn.travelassistant.data.local.model.LocalPoiDetailSnapshot

@Dao
interface PoiContentDao {
    @Upsert
    suspend fun upsertPoisInternal(pois: List<LocalPoiEntity>)

    @Transaction
    suspend fun upsertPois(pois: List<LocalPoiEntity>) {
        if (pois.isEmpty()) return
        upsertPoisInternal(pois)
        rebuildSearchIndex(pois.map(LocalPoiEntity::poiId))
    }

    @Upsert
    suspend fun upsertAliasesInternal(aliases: List<LocalPoiAliasEntity>)

    @Transaction
    suspend fun upsertAliases(aliases: List<LocalPoiAliasEntity>) {
        if (aliases.isEmpty()) return
        val previousPoiIds = getAliasesByIds(aliases.map(LocalPoiAliasEntity::aliasId))
            .map(LocalPoiAliasEntity::poiId)
        upsertAliasesInternal(aliases)
        rebuildSearchIndex(previousPoiIds + aliases.map(LocalPoiAliasEntity::poiId))
    }

    @Upsert
    suspend fun upsertMenuItemsInternal(menuItems: List<LocalMenuItemEntity>)

    @Transaction
    suspend fun upsertMenuItems(menuItems: List<LocalMenuItemEntity>) {
        if (menuItems.isEmpty()) return
        val previousPoiIds = getMenuItemsByIds(menuItems.map(LocalMenuItemEntity::menuItemId))
            .map(LocalMenuItemEntity::poiId)
        upsertMenuItemsInternal(menuItems)
        rebuildSearchIndex(previousPoiIds + menuItems.map(LocalMenuItemEntity::poiId))
    }

    @Upsert
    suspend fun upsertNarrations(narrations: List<LocalNarrationEntity>)

    @Upsert
    suspend fun upsertCultureItems(cultureItems: List<LocalCultureEntity>)

    @Query("SELECT * FROM local_pois WHERE poi_id = :poiId LIMIT 1")
    suspend fun getPoiById(poiId: String): LocalPoiEntity?

    @Query("SELECT * FROM local_pois WHERE city = :city ORDER BY name, poi_id")
    suspend fun getPoisByCity(city: String): List<LocalPoiEntity>

    @Query(
        """
        SELECT * FROM local_pois
        WHERE city = :city
          AND EXISTS (
              SELECT 1 FROM travel_packages
              WHERE city = :city
                AND package_id != ''
                AND version != ''
                AND manifest_json != ''
                AND published_at_epoch_millis > 0
          )
        ORDER BY poi_id
        """,
    )
    suspend fun getActivePackagePoisByCity(city: String): List<LocalPoiEntity>

    @Query(
        """
        SELECT DISTINCT local_pois.* FROM local_pois
        INNER JOIN local_poi_search_fts
            ON local_poi_search_fts.poi_id = local_pois.poi_id
        WHERE local_pois.city = :city
          AND EXISTS (
              SELECT 1 FROM travel_packages
              WHERE city = :city
                AND package_id != ''
                AND version != ''
                AND manifest_json != ''
                AND published_at_epoch_millis > 0
          )
          AND local_poi_search_fts MATCH :matchExpression
        ORDER BY local_pois.poi_id
        """,
    )
    suspend fun searchActivePackagePois(
        city: String,
        matchExpression: String,
    ): List<LocalPoiEntity>

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
    suspend fun getNarration(
        poiId: String,
        languageCode: String,
    ): LocalNarrationEntity?

    @Transaction
    suspend fun getPoiDetailSnapshot(
        poiId: String,
        languageCode: String,
    ): LocalPoiDetailSnapshot? {
        val poi = getPoiById(poiId) ?: return null
        return LocalPoiDetailSnapshot(
            poi = poi,
            menuItems = getMenuItemsForPoi(poiId),
            narration = getNarration(poiId, languageCode),
        )
    }

    @Query("SELECT * FROM local_culture_items WHERE city = :city ORDER BY topic, culture_item_id")
    suspend fun getCultureByCity(city: String): List<LocalCultureEntity>

    @Query("SELECT * FROM local_culture_items WHERE area = :area ORDER BY topic, culture_item_id")
    suspend fun getCultureByArea(area: String): List<LocalCultureEntity>

    @Query("DELETE FROM local_pois WHERE poi_id = :poiId")
    suspend fun deletePoiInternal(poiId: String): Int

    @Transaction
    suspend fun deletePoi(poiId: String): Int {
        deleteSearchIndexForPois(listOf(poiId))
        return deletePoiInternal(poiId)
    }

    @Query("DELETE FROM local_pois WHERE city = :city")
    suspend fun deletePoisByCityInternal(city: String): Int

    @Transaction
    suspend fun deletePoisByCity(city: String): Int {
        val poiIds = getPoiIdsByCity(city)
        if (poiIds.isNotEmpty()) deleteSearchIndexForPois(poiIds)
        return deletePoisByCityInternal(city)
    }

    @Query("DELETE FROM local_culture_items WHERE city = :city")
    suspend fun deleteCultureByCity(city: String): Int

    @Query("SELECT poi_id FROM local_pois WHERE city = :city ORDER BY poi_id")
    suspend fun getPoiIdsByCity(city: String): List<String>

    @Query("SELECT * FROM local_pois WHERE poi_id IN (:poiIds) ORDER BY poi_id")
    suspend fun getPoisByIds(poiIds: List<String>): List<LocalPoiEntity>

    @Query("SELECT * FROM local_poi_aliases WHERE alias_id IN (:aliasIds) ORDER BY alias_id")
    suspend fun getAliasesByIds(
        aliasIds: List<String>,
    ): List<LocalPoiAliasEntity>

    @Query(
        """
        SELECT * FROM local_menu_items
        WHERE menu_item_id IN (:menuItemIds)
        ORDER BY menu_item_id
        """,
    )
    suspend fun getMenuItemsByIds(
        menuItemIds: List<String>,
    ): List<LocalMenuItemEntity>

    @Query(
        """
        SELECT * FROM local_menu_items
        WHERE poi_id IN (:poiIds)
        ORDER BY poi_id, menu_item_id
        """,
    )
    suspend fun getMenuItemsForPois(
        poiIds: List<String>,
    ): List<LocalMenuItemEntity>

    @Query("DELETE FROM local_poi_search_fts WHERE poi_id IN (:poiIds)")
    suspend fun deleteSearchIndexForPois(poiIds: List<String>): Int

    @Insert
    suspend fun insertSearchIndexRows(rows: List<LocalPoiSearchFtsEntity>)

    private suspend fun rebuildSearchIndex(poiIds: List<String>) {
        val stablePoiIds = poiIds.distinct().sorted()
        if (stablePoiIds.isEmpty()) return

        deleteSearchIndexForPois(stablePoiIds)
        val pois = getPoisByIds(stablePoiIds)
        if (pois.isEmpty()) return

        val existingPoiIds = pois.map(LocalPoiEntity::poiId)
        val aliasesByPoiId = getAliasesForPois(existingPoiIds)
            .groupBy(LocalPoiAliasEntity::poiId)
        val menuItemsByPoiId = getMenuItemsForPois(existingPoiIds)
            .groupBy(LocalMenuItemEntity::poiId)
        insertSearchIndexRows(
            pois.map { poi ->
                PoiSearchIndexBuilder.build(
                    poi = poi,
                    aliases = aliasesByPoiId[poi.poiId].orEmpty(),
                    menuItems = menuItemsByPoiId[poi.poiId].orEmpty(),
                )
            },
        )
    }
}
