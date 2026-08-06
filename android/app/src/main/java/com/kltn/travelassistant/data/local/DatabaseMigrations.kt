package com.kltn.travelassistant.data.local

import androidx.room.migration.Migration
import androidx.sqlite.db.SupportSQLiteDatabase
import com.kltn.travelassistant.data.local.entity.LocalMenuItemEntity
import com.kltn.travelassistant.data.local.entity.LocalPoiAliasEntity
import com.kltn.travelassistant.data.local.entity.LocalPoiEntity

object DatabaseMigrations {
    val MIGRATION_1_2 = object : Migration(1, 2) {
        override fun migrate(db: SupportSQLiteDatabase) {
            db.execSQL(
                "ALTER TABLE local_narrations ADD COLUMN source_label TEXT DEFAULT NULL",
            )
        }
    }

    val MIGRATION_2_3 = object : Migration(2, 3) {
        override fun migrate(db: SupportSQLiteDatabase) {
            val legacyAccount = "0".repeat(64)
            db.execSQL(
                "ALTER TABLE local_itineraries ADD COLUMN account_key TEXT " +
                    "NOT NULL DEFAULT '$legacyAccount'",
            )
            db.execSQL(
                "ALTER TABLE local_itineraries ADD COLUMN city TEXT NOT NULL DEFAULT 'hcmc'",
            )
            db.execSQL(
                "ALTER TABLE local_itineraries ADD COLUMN local_date TEXT " +
                    "NOT NULL DEFAULT '1970-01-01'",
            )
            db.execSQL(
                "ALTER TABLE local_itineraries ADD COLUMN timezone TEXT " +
                    "NOT NULL DEFAULT 'Asia/Ho_Chi_Minh'",
            )
            db.execSQL(
                "ALTER TABLE local_itineraries ADD COLUMN start_local_time TEXT " +
                    "NOT NULL DEFAULT '00:00'",
            )
            db.execSQL(
                "ALTER TABLE local_itineraries ADD COLUMN end_local_time TEXT " +
                    "NOT NULL DEFAULT '23:59'",
            )
            db.execSQL(
                "ALTER TABLE local_itineraries ADD COLUMN assumptions_json TEXT " +
                    "NOT NULL DEFAULT '[]'",
            )
            db.execSQL(
                "ALTER TABLE local_itineraries ADD COLUMN warnings_json TEXT " +
                    "NOT NULL DEFAULT '[]'",
            )
            db.execSQL(
                "ALTER TABLE local_itineraries ADD COLUMN local_revision INTEGER " +
                    "NOT NULL DEFAULT 0",
            )
            db.execSQL(
                "ALTER TABLE local_itineraries ADD COLUMN server_revision INTEGER " +
                    "NOT NULL DEFAULT 0",
            )
            db.execSQL(
                "ALTER TABLE local_itineraries ADD COLUMN sync_state TEXT " +
                    "NOT NULL DEFAULT 'failed'",
            )
            db.execSQL(
                "ALTER TABLE local_itineraries ADD COLUMN is_deleted INTEGER " +
                    "NOT NULL DEFAULT 0",
            )
            db.execSQL(
                """
                CREATE INDEX IF NOT EXISTS index_local_itineraries_account_deleted_date_updated
                ON local_itineraries(account_key, is_deleted, local_date, updated_at_epoch_millis)
                """.trimIndent(),
            )
        }
    }

    val MIGRATION_3_4 = object : Migration(3, 4) {
        override fun migrate(db: SupportSQLiteDatabase) {
            db.execSQL(
                """
                CREATE VIRTUAL TABLE IF NOT EXISTS local_poi_search_fts
                USING FTS4(
                    poi_id TEXT NOT NULL,
                    normalized_name TEXT NOT NULL,
                    normalized_aliases TEXT NOT NULL,
                    normalized_dishes TEXT NOT NULL,
                    normalized_categories TEXT NOT NULL,
                    tokenize=unicode61,
                    notindexed=`poi_id`
                )
                """.trimIndent(),
            )
            rebuildPoiSearchIndex(db)
        }
    }

    private fun rebuildPoiSearchIndex(db: SupportSQLiteDatabase) {
        val pois = db.query(
            """
            SELECT poi_id, name, city, area, category, latitude, longitude, address,
                   short_description, status, updated_at_epoch_millis
            FROM local_pois
            ORDER BY poi_id
            """.trimIndent(),
        ).use { cursor ->
            buildList {
                while (cursor.moveToNext()) {
                    add(
                        LocalPoiEntity(
                            poiId = cursor.getString(0),
                            name = cursor.getString(1),
                            city = cursor.getString(2),
                            area = cursor.getStringOrNull(3),
                            category = cursor.getString(4),
                            latitude = cursor.getDouble(5),
                            longitude = cursor.getDouble(6),
                            address = cursor.getStringOrNull(7),
                            shortDescription = cursor.getStringOrNull(8),
                            status = cursor.getString(9),
                            updatedAtEpochMillis = cursor.getLong(10),
                        ),
                    )
                }
            }
        }
        val aliasesByPoiId = db.query(
            """
            SELECT alias_id, poi_id, alias, normalized_alias, language_code
            FROM local_poi_aliases
            ORDER BY alias_id
            """.trimIndent(),
        ).use { cursor ->
            buildList {
                while (cursor.moveToNext()) {
                    add(
                        LocalPoiAliasEntity(
                            aliasId = cursor.getString(0),
                            poiId = cursor.getString(1),
                            alias = cursor.getString(2),
                            normalizedAlias = cursor.getString(3),
                            languageCode = cursor.getStringOrNull(4),
                        ),
                    )
                }
            }.groupBy(LocalPoiAliasEntity::poiId)
        }
        val menuItemsByPoiId = db.query(
            """
            SELECT menu_item_id, poi_id, dish_name, price_minor_units, currency_code,
                   source_type, updated_at_epoch_millis
            FROM local_menu_items
            ORDER BY menu_item_id
            """.trimIndent(),
        ).use { cursor ->
            buildList {
                while (cursor.moveToNext()) {
                    add(
                        LocalMenuItemEntity(
                            menuItemId = cursor.getString(0),
                            poiId = cursor.getString(1),
                            dishName = cursor.getString(2),
                            priceMinorUnits = cursor.getLong(3),
                            currencyCode = cursor.getString(4),
                            sourceType = cursor.getString(5),
                            updatedAtEpochMillis = cursor.getLong(6),
                        ),
                    )
                }
            }.groupBy(LocalMenuItemEntity::poiId)
        }

        db.compileStatement(
            """
            INSERT INTO local_poi_search_fts (
                poi_id, normalized_name, normalized_aliases,
                normalized_dishes, normalized_categories
            ) VALUES (?, ?, ?, ?, ?)
            """.trimIndent(),
        ).use { statement ->
            pois.forEach { poi ->
                val row = PoiSearchIndexBuilder.build(
                    poi = poi,
                    aliases = aliasesByPoiId[poi.poiId].orEmpty(),
                    menuItems = menuItemsByPoiId[poi.poiId].orEmpty(),
                )
                statement.bindString(1, row.poiId)
                statement.bindString(2, row.normalizedName)
                statement.bindString(3, row.normalizedAliases)
                statement.bindString(4, row.normalizedDishes)
                statement.bindString(5, row.normalizedCategories)
                statement.executeInsert()
                statement.clearBindings()
            }
        }
    }

    private fun android.database.Cursor.getStringOrNull(columnIndex: Int): String? =
        if (isNull(columnIndex)) null else getString(columnIndex)
}
