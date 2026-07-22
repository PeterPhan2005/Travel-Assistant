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

    private companion object {
        const val TEST_DATABASE = "t017-migration-test"
    }
}
