package com.kltn.travelassistant.data.local

import androidx.room.migration.Migration
import androidx.sqlite.db.SupportSQLiteDatabase

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
}
