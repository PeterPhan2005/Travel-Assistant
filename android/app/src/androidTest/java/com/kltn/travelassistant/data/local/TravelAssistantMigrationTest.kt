package com.kltn.travelassistant.data.local

import androidx.room.testing.MigrationTestHelper
import androidx.sqlite.db.SupportSQLiteDatabase
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class TravelAssistantMigrationTest {
    @get:Rule
    val migrationHelper = MigrationTestHelper(
        InstrumentationRegistry.getInstrumentation(),
        TravelAssistantDatabase::class.java,
    )

    @Test
    fun migrationOneToTwoPreservesPoiAndAddsNullableNarrationSourceLabel() {
        migrationHelper.createDatabase(TEST_DATABASE, 1).apply {
            insertVersionOnePoi()
            insertVersionOneNarration()
            close()
        }

        val migrated = migrationHelper.runMigrationsAndValidate(
            TEST_DATABASE,
            2,
            true,
            DatabaseMigrations.MIGRATION_1_2,
        )

        migrated.query("SELECT name FROM local_pois WHERE poi_id = 'poi-1'").use { cursor ->
            assertTrue(cursor.moveToFirst())
            assertEquals("Điểm đã lưu", cursor.getString(0))
        }
        migrated.query(
            "SELECT source_label FROM local_narrations WHERE narration_id = 'narration-1'",
        ).use { cursor ->
            assertTrue(cursor.moveToFirst())
            assertTrue(cursor.isNull(0))
        }
        migrated.query("PRAGMA table_info(local_narrations)").use { cursor ->
            val nameIndex = cursor.getColumnIndexOrThrow("name")
            var sourceLabelExists = false
            while (cursor.moveToNext()) {
                sourceLabelExists = sourceLabelExists || cursor.getString(nameIndex) == "source_label"
            }
            assertTrue(sourceLabelExists)
        }
        migrated.close()
    }

    @Test
    fun migrationTwoToThreePreservesLegacyRowsBehindAnInaccessibleAccountKey() {
        migrationHelper.createDatabase(TEST_DATABASE_V2, 2).apply {
            execSQL(
                """
                INSERT INTO local_itineraries (
                    itinerary_id, title, created_at_epoch_millis, updated_at_epoch_millis
                ) VALUES ('legacy-itinerary', 'Legacy title', 100, 200)
                """.trimIndent(),
            )
            close()
        }

        val migrated = migrationHelper.runMigrationsAndValidate(
            TEST_DATABASE_V2,
            3,
            true,
            DatabaseMigrations.MIGRATION_2_3,
        )

        migrated.query(
            """
            SELECT account_key, city, local_date, timezone, local_revision,
                   server_revision, sync_state, is_deleted
            FROM local_itineraries WHERE itinerary_id = 'legacy-itinerary'
            """.trimIndent(),
        ).use { cursor ->
            assertTrue(cursor.moveToFirst())
            assertEquals("0".repeat(64), cursor.getString(0))
            assertEquals("hcmc", cursor.getString(1))
            assertEquals("1970-01-01", cursor.getString(2))
            assertEquals("Asia/Ho_Chi_Minh", cursor.getString(3))
            assertEquals(0L, cursor.getLong(4))
            assertEquals(0L, cursor.getLong(5))
            assertEquals("failed", cursor.getString(6))
            assertEquals(0, cursor.getInt(7))
        }
        migrated.query("PRAGMA index_list(local_itineraries)").use { cursor ->
            val nameIndex = cursor.getColumnIndexOrThrow("name")
            var accountIndexExists = false
            while (cursor.moveToNext()) {
                accountIndexExists = accountIndexExists || cursor.getString(nameIndex) ==
                    "index_local_itineraries_account_deleted_date_updated"
            }
            assertTrue(accountIndexExists)
        }
        migrated.close()
    }

    @Test
    fun migrationThreeToFourBuildsFtsAndPreservesAccountOwnedItineraryState() {
        migrationHelper.createDatabase(TEST_DATABASE_V3, 3).apply {
            insertVersionThreeSearchAndItineraryRows()
            close()
        }

        val migrated = migrationHelper.runMigrationsAndValidate(
            TEST_DATABASE_V3,
            4,
            true,
            DatabaseMigrations.MIGRATION_3_4,
        )

        migrated.query(
            """
            SELECT poi_id FROM local_poi_search_fts
            WHERE local_poi_search_fts MATCH ?
            """.trimIndent(),
            arrayOf("\"pho*\""),
        ).use { cursor ->
            assertTrue(cursor.moveToFirst())
            assertEquals("poi-1", cursor.getString(0))
            assertEquals(1, cursor.count)
        }
        migrated.query(
            """
            SELECT normalized_name, normalized_aliases, normalized_dishes,
                   normalized_categories
            FROM local_poi_search_fts WHERE poi_id = 'poi-1'
            """.trimIndent(),
        ).use { cursor ->
            assertTrue(cursor.moveToFirst())
            assertEquals("diem da luu", cursor.getString(0))
            assertEquals("buu dien sai gon", cursor.getString(1))
            assertEquals("pho bo", cursor.getString(2))
            assertEquals("museum bao tang", cursor.getString(3))
        }
        migrated.query(
            """
            SELECT account_key, city, local_date, timezone, start_local_time,
                   end_local_time, assumptions_json, warnings_json, local_revision,
                   server_revision, sync_state, is_deleted
            FROM local_itineraries WHERE itinerary_id = 'itinerary-1'
            """.trimIndent(),
        ).use { cursor ->
            assertTrue(cursor.moveToFirst())
            assertEquals("a".repeat(64), cursor.getString(0))
            assertEquals("hcmc", cursor.getString(1))
            assertEquals("2026-08-04", cursor.getString(2))
            assertEquals("Asia/Ho_Chi_Minh", cursor.getString(3))
            assertEquals("09:00", cursor.getString(4))
            assertEquals("17:00", cursor.getString(5))
            assertEquals("[\"Giữ snapshot\"]", cursor.getString(6))
            assertEquals("[\"Giữ warning\"]", cursor.getString(7))
            assertEquals(7L, cursor.getLong(8))
            assertEquals(5L, cursor.getLong(9))
            assertEquals("conflict", cursor.getString(10))
            assertEquals(0, cursor.getInt(11))
        }
        migrated.query(
            """
            SELECT poi_id, title, position FROM local_itinerary_items
            WHERE itinerary_item_id = 'item-1'
            """.trimIndent(),
        ).use { cursor ->
            assertTrue(cursor.moveToFirst())
            assertEquals("poi-1", cursor.getString(0))
            assertEquals("Điểm đã lưu", cursor.getString(1))
            assertEquals(0, cursor.getInt(2))
        }
        migrated.query("PRAGMA foreign_key_check").use { cursor ->
            assertEquals(0, cursor.count)
        }
        migrated.close()
    }

    private fun SupportSQLiteDatabase.insertVersionOnePoi() {
        execSQL(
            """
            INSERT INTO local_pois (
                poi_id, name, city, area, category, latitude, longitude,
                address, short_description, status, updated_at_epoch_millis
            ) VALUES (
                'poi-1', 'Điểm đã lưu', 'Ho Chi Minh City', NULL, 'landmark',
                10.0, 106.0, NULL, NULL, 'active', 1721510400000
            )
            """.trimIndent(),
        )
    }

    private fun SupportSQLiteDatabase.insertVersionOneNarration() {
        execSQL(
            """
            INSERT INTO local_narrations (
                narration_id, poi_id, language_code, content,
                verification_status, generated_at_epoch_millis
            ) VALUES (
                'narration-1', 'poi-1', 'vi', 'Nội dung cũ', 'verified', 1721510400000
            )
            """.trimIndent(),
        )
    }

    private fun SupportSQLiteDatabase.insertVersionThreeSearchAndItineraryRows() {
        insertVersionOnePoi()
        execSQL(
            """
            INSERT INTO local_poi_aliases (
                alias_id, poi_id, alias, normalized_alias, language_code
            ) VALUES ('alias-1', 'poi-1', 'Bưu điện Sài Gòn', 'buu dien sai gon', 'vi')
            """.trimIndent(),
        )
        execSQL(
            """
            INSERT INTO local_menu_items (
                menu_item_id, poi_id, dish_name, price_minor_units, currency_code,
                source_type, updated_at_epoch_millis
            ) VALUES ('menu-1', 'poi-1', 'Phở bò', 75000, 'VND', 'official_operator', 1)
            """.trimIndent(),
        )
        execSQL(
            """
            UPDATE local_pois SET category = 'museum' WHERE poi_id = 'poi-1'
            """.trimIndent(),
        )
        execSQL(
            """
            INSERT INTO travel_packages (
                package_id, city, version, manifest_json, published_at_epoch_millis
            ) VALUES ('package-1', 'Ho Chi Minh City', '1.0.0', '{}', 1)
            """.trimIndent(),
        )
        execSQL(
            """
            INSERT INTO local_itineraries (
                itinerary_id, title, account_key, city, local_date, timezone,
                start_local_time, end_local_time, assumptions_json, warnings_json,
                local_revision, server_revision, sync_state, is_deleted,
                created_at_epoch_millis, updated_at_epoch_millis
            ) VALUES (
                'itinerary-1', 'Ngày đã lưu', '${"a".repeat(64)}', 'hcmc',
                '2026-08-04', 'Asia/Ho_Chi_Minh', '09:00', '17:00',
                '["Giữ snapshot"]', '["Giữ warning"]', 7, 5, 'conflict', 0, 1, 2
            )
            """.trimIndent(),
        )
        execSQL(
            """
            INSERT INTO local_itinerary_items (
                itinerary_item_id, itinerary_id, poi_id, title, position,
                start_at_epoch_millis, end_at_epoch_millis, travel_time_minutes, notes
            ) VALUES (
                'item-1', 'itinerary-1', 'poi-1', 'Điểm đã lưu', 0,
                1, 2, NULL, NULL
            )
            """.trimIndent(),
        )
    }

    private companion object {
        const val TEST_DATABASE = "t017-migration-test"
        const val TEST_DATABASE_V2 = "t071-migration-test"
        const val TEST_DATABASE_V3 = "t080-migration-test"
    }
}
