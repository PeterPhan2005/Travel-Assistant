package com.kltn.travelassistant.feature.poi.presentation

import java.time.ZoneOffset
import java.util.Locale
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class PoiDetailFormattersTest {
    @Test
    fun vndUsesZeroFractionDigits() {
        assertEquals(
            "50.000 ₫",
            CurrencyFormatter.format(50_000, "VND", Locale.forLanguageTag("vi-VN")),
        )
    }

    @Test
    fun usdUsesDecimalMinorUnits() {
        assertEquals(
            "$12.34",
            CurrencyFormatter.format(1_234, "USD", Locale.US),
        )
    }

    @Test
    fun timestampUsesRequestedLocaleAndZone() {
        assertEquals(
            "7/20/24",
            PriceUpdateDateFormatter.format(
                epochMillis = 1_721_510_400_000,
                locale = Locale.US,
                zoneId = ZoneOffset.UTC,
            ),
        )
    }

    @Test
    fun invalidValuesFailSafely() {
        assertNull(CurrencyFormatter.format(-1, "VND", Locale.US))
        assertNull(CurrencyFormatter.format(100, "not-a-currency", Locale.US))
        assertNull(PriceUpdateDateFormatter.format(0, Locale.US, ZoneOffset.UTC))
    }
}
