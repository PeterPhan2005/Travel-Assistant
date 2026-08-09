package com.kltn.travelassistant.analytics

import android.content.ContentProvider
import android.content.ContentValues
import android.database.Cursor
import android.database.MatrixCursor
import android.net.Uri
import dagger.hilt.android.EntryPointAccessors

class DebugProductAnalyticsProvider : ContentProvider() {
    override fun onCreate(): Boolean = true

    override fun query(
        uri: Uri,
        projection: Array<out String>?,
        selection: String?,
        selectionArgs: Array<out String>?,
        sortOrder: String?,
    ): Cursor {
        require(uri.pathSegments == listOf(EVENTS_PATH))
        require(projection == null && selection == null && selectionArgs == null && sortOrder == null)
        val cursor = MatrixCursor(COLUMNS)
        inspector().snapshot().forEach { record ->
            val properties = ProductAnalyticsSchema.properties(record.event)
                .joinToString(PROPERTY_SEPARATOR) { property ->
                    "${property.key.wireValue}${KEY_VALUE_SEPARATOR}${property.value}"
                }
            cursor.addRow(
                arrayOf<Any?>(
                    record.sequence,
                    record.schemaVersion,
                    ProductAnalyticsSchema.eventName(record.event).wireValue,
                    properties,
                ),
            )
        }
        cursor.setNotificationUri(requireNotNull(context).contentResolver, uri)
        return cursor
    }

    override fun delete(
        uri: Uri,
        selection: String?,
        selectionArgs: Array<out String>?,
    ): Int {
        require(uri.pathSegments == listOf(EVENTS_PATH))
        require(selection == null && selectionArgs == null)
        val count = inspector().snapshot().size
        inspector().clear()
        requireNotNull(context).contentResolver.notifyChange(uri, null)
        return count
    }

    override fun getType(uri: Uri): String {
        require(uri.pathSegments == listOf(EVENTS_PATH))
        return CONTENT_TYPE
    }

    override fun insert(uri: Uri, values: ContentValues?): Uri? =
        throw UnsupportedOperationException("Debug analytics is read-only")

    override fun update(
        uri: Uri,
        values: ContentValues?,
        selection: String?,
        selectionArgs: Array<out String>?,
    ): Int = throw UnsupportedOperationException("Debug analytics is read-only")

    private fun inspector(): DebugProductAnalyticsInspector {
        val applicationContext = requireNotNull(context).applicationContext
        return EntryPointAccessors.fromApplication(
            applicationContext,
            ProductAnalyticsDebugEntryPoint::class.java,
        ).debugProductAnalyticsInspector()
    }

    companion object {
        const val AUTHORITY = "com.kltn.travelassistant.analytics"
        val EVENTS_URI: Uri = Uri.parse("content://$AUTHORITY/$EVENTS_PATH")

        const val COLUMN_SEQUENCE = "sequence"
        const val COLUMN_SCHEMA_VERSION = "schema_version"
        const val COLUMN_EVENT_NAME = "event_name"
        const val COLUMN_PROPERTIES = "properties"

        private const val EVENTS_PATH = "events"
        private const val PROPERTY_SEPARATOR = ","
        private const val KEY_VALUE_SEPARATOR = "="
        private const val CONTENT_TYPE = "vnd.android.cursor.dir/vnd.travelassistant.analytics-event"
        private val COLUMNS = arrayOf(
            COLUMN_SEQUENCE,
            COLUMN_SCHEMA_VERSION,
            COLUMN_EVENT_NAME,
            COLUMN_PROPERTIES,
        )
    }
}
