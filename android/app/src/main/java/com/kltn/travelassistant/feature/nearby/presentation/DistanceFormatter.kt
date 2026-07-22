package com.kltn.travelassistant.feature.nearby.presentation

import java.math.RoundingMode
import java.text.DecimalFormat
import java.text.DecimalFormatSymbols
import java.util.Locale

object DistanceFormatter {
    fun formatKilometresValue(
        distanceMeters: Double,
        locale: Locale = Locale.getDefault(),
    ): String {
        require(distanceMeters.isFinite() && distanceMeters >= 0.0)
        val formatter = DecimalFormat("0.0", DecimalFormatSymbols.getInstance(locale)).apply {
            roundingMode = RoundingMode.HALF_UP
        }
        return formatter.format(distanceMeters / 1_000.0)
    }
}
