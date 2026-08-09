package com.kltn.travelassistant.analytics

import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import dagger.hilt.android.EntryPointAccessors
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class ProductAnalyticsDebugInspectionTest {
    @Test
    fun debugProviderExposesExactSafeInMemorySchemaAndCanClearIt() {
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        val entryPoint = EntryPointAccessors.fromApplication(
            context.applicationContext,
            ProductAnalyticsDebugEntryPoint::class.java,
        )
        entryPoint.debugProductAnalyticsInspector().clear()
        entryPoint.productAnalytics().track(ProductAnalyticsEvent.TripReturn)
        entryPoint.productAnalytics().track(
            ProductAnalyticsEvent.GeocontextOpened(GeocontextResultState.EMPTY),
        )

        val rows = mutableListOf<List<String>>()
        context.contentResolver.query(
            DebugProductAnalyticsProvider.EVENTS_URI,
            null,
            null,
            null,
            null,
        ).use { cursor ->
            requireNotNull(cursor)
            assertEquals(
                listOf(
                    DebugProductAnalyticsProvider.COLUMN_SEQUENCE,
                    DebugProductAnalyticsProvider.COLUMN_SCHEMA_VERSION,
                    DebugProductAnalyticsProvider.COLUMN_EVENT_NAME,
                    DebugProductAnalyticsProvider.COLUMN_PROPERTIES,
                ),
                cursor.columnNames.toList(),
            )
            while (cursor.moveToNext()) {
                rows += cursor.columnNames.indices.map(cursor::getString)
            }
        }

        assertEquals(
            listOf(
                listOf("1", "1", "trip_return", ""),
                listOf("2", "1", "geocontext_opened", "result_state=empty"),
            ),
            rows,
        )
        assertEquals(
            2,
            context.contentResolver.delete(
                DebugProductAnalyticsProvider.EVENTS_URI,
                null,
                null,
            ),
        )
        assertTrue(entryPoint.debugProductAnalyticsInspector().snapshot().isEmpty())
    }
}
