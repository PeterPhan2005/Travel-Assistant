package com.kltn.travelassistant.feature.nearby.presentation

import java.util.Locale
import org.junit.Assert.assertEquals
import org.junit.Test

class DistanceFormatterTest {
    @Test
    fun formatsKilometresWithOneDecimalAndStableHalfUpRounding() {
        assertEquals("0,0", DistanceFormatter.formatKilometresValue(0.0, Locale.GERMANY))
        assertEquals("0,3", DistanceFormatter.formatKilometresValue(250.0, Locale.GERMANY))
        assertEquals("1,2", DistanceFormatter.formatKilometresValue(1_240.0, Locale.GERMANY))
    }
}
