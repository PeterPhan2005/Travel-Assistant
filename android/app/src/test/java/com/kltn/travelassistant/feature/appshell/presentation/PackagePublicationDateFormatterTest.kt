package com.kltn.travelassistant.feature.appshell.presentation

import java.time.ZoneId
import java.util.Locale
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class PackagePublicationDateFormatterTest {
    @Test
    fun validTimestampUsesRequestedLocaleAndTimeZone() {
        assertEquals(
            "Jul 20, 2024",
            PackagePublicationDateFormatter.format(
                publishedAtEpochMillis = 1_721_520_000_000L,
                locale = Locale.US,
                zoneId = ZoneId.of("America/Los_Angeles"),
            ),
        )
        assertEquals(
            "21 Jul 2024",
            PackagePublicationDateFormatter.format(
                publishedAtEpochMillis = 1_721_520_000_000L,
                locale = Locale.UK,
                zoneId = ZoneId.of("UTC"),
            ),
        )
    }

    @Test
    fun invalidTimestampFailsSafely() {
        assertNull(PackagePublicationDateFormatter.format(0L, Locale.US, ZoneId.of("UTC")))
        assertNull(PackagePublicationDateFormatter.format(-1L, Locale.US, ZoneId.of("UTC")))
    }
}
