package com.kltn.travelassistant.feature.poi.presentation

import java.time.Instant
import java.time.ZoneId
import java.time.format.DateTimeFormatter
import java.time.format.FormatStyle
import java.util.Locale

object PriceUpdateDateFormatter {
    fun format(
        epochMillis: Long,
        locale: Locale = Locale.getDefault(),
        zoneId: ZoneId = ZoneId.systemDefault(),
    ): String? {
        if (epochMillis <= 0) return null
        return runCatching {
            DateTimeFormatter.ofLocalizedDate(FormatStyle.SHORT)
                .withLocale(locale)
                .withZone(zoneId)
                .format(Instant.ofEpochMilli(epochMillis))
        }.getOrNull()
    }
}
