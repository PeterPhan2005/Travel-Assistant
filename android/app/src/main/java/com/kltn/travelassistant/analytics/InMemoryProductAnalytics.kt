package com.kltn.travelassistant.analytics

import java.util.ArrayDeque

internal data class DebugProductAnalyticsRecord(
    val sequence: Long,
    val schemaVersion: Int,
    val event: ProductAnalyticsEvent,
)

internal interface DebugProductAnalyticsInspector {
    fun snapshot(): List<DebugProductAnalyticsRecord>

    fun clear()
}

internal class InMemoryProductAnalytics(
    private val enabled: Boolean,
    private val capacity: Int = DEFAULT_CAPACITY,
) : ProductAnalytics, DebugProductAnalyticsInspector {
    private val lock = Any()
    private val records = ArrayDeque<DebugProductAnalyticsRecord>()
    private var nextSequence = 1L
    private var activeDetailPoiId: String? = null
    private var navigationRequestedForActiveDetail = false

    init {
        require(capacity in 1..MAXIMUM_CAPACITY)
    }

    override fun track(event: ProductAnalyticsEvent) {
        if (!enabled) return
        synchronized(lock) {
            if (!acceptEvent(event)) return
            if (records.size == capacity) records.removeFirst()
            records.addLast(
                DebugProductAnalyticsRecord(
                    sequence = nextSequence++,
                    schemaVersion = PRODUCT_ANALYTICS_SCHEMA_VERSION,
                    event = event,
                ),
            )
        }
    }

    override fun snapshot(): List<DebugProductAnalyticsRecord> = synchronized(lock) {
        records.toList()
    }

    override fun clear() {
        synchronized(lock) {
            records.clear()
            nextSequence = 1L
            activeDetailPoiId = null
            navigationRequestedForActiveDetail = false
        }
    }

    private fun acceptEvent(event: ProductAnalyticsEvent): Boolean = when (event) {
        is ProductAnalyticsEvent.NavigationConversion -> when (event.stage) {
            NavigationConversionStage.DETAIL_OPENED -> {
                activeDetailPoiId = event.poiId
                navigationRequestedForActiveDetail = false
                true
            }
            NavigationConversionStage.NAVIGATION_REQUESTED -> {
                if (
                    activeDetailPoiId != event.poiId ||
                    navigationRequestedForActiveDetail
                ) {
                    false
                } else {
                    navigationRequestedForActiveDetail = true
                    true
                }
            }
        }
        else -> true
    }

    private companion object {
        const val DEFAULT_CAPACITY = 200
        const val MAXIMUM_CAPACITY = 1_000
    }
}
