package com.kltn.travelassistant.feature.assistant.presentation

import com.kltn.travelassistant.feature.assistant.domain.AssistantPrice
import java.text.NumberFormat
import java.time.OffsetDateTime
import java.time.format.DateTimeFormatter
import java.util.Locale

private val VIETNAMESE_LOCALE = Locale.forLanguageTag("vi-VN")

internal fun formatAssistantDistance(distanceMetres: Double): String =
    String.format(VIETNAMESE_LOCALE, "%.1f km", distanceMetres / 1_000.0)

internal fun formatAssistantRating(
    rating: Double,
    ratingCount: Int?,
): String = if (ratingCount == null) {
    String.format(VIETNAMESE_LOCALE, "%.1f ★", rating)
} else {
    String.format(VIETNAMESE_LOCALE, "%.1f ★ (%d)", rating, ratingCount)
}

internal fun formatAssistantPrice(price: AssistantPrice): String {
    val amount = NumberFormat.getIntegerInstance(VIETNAMESE_LOCALE)
        .format(price.minorUnits)
    val date = OffsetDateTime.parse(price.updatedAt)
        .format(DateTimeFormatter.ofPattern("dd/MM/yyyy"))
    return "$amount ${price.currency} · cập nhật $date"
}
