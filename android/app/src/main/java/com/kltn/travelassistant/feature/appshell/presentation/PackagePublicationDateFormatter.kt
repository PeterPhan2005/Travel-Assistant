package com.kltn.travelassistant.feature.appshell.presentation

import java.time.DateTimeException
import java.time.Instant
import java.time.ZoneId
import java.time.format.DateTimeFormatter
import java.time.format.FormatStyle
import java.util.Locale

object PackagePublicationDateFormatter {
    fun format(
        publishedAtEpochMillis: Long,
        locale: Locale = Locale.getDefault(),
        zoneId: ZoneId = ZoneId.systemDefault(),
    ): String? {
        if (publishedAtEpochMillis <= 0) return null
        return try {
            val date = Instant.ofEpochMilli(publishedAtEpochMillis)
                .atZone(zoneId)
                .toLocalDate()
            DateTimeFormatter.ofLocalizedDate(FormatStyle.MEDIUM)
                .withLocale(locale)
                .format(date)
        } catch (_: DateTimeException) {
            null
        } catch (_: ArithmeticException) {
            null
        }
    }
}
