package com.kltn.travelassistant.feature.poi.presentation

import java.math.BigDecimal
import java.text.NumberFormat
import java.util.Currency
import java.util.Locale

object CurrencyFormatter {
    fun format(
        priceMinorUnits: Long,
        currencyCode: String,
        locale: Locale = Locale.getDefault(),
    ): String? {
        if (priceMinorUnits < 0 || currencyCode.isBlank()) return null
        return runCatching {
            val currency = Currency.getInstance(currencyCode.uppercase(Locale.ROOT))
            val fractionDigits = currency.defaultFractionDigits
            require(fractionDigits >= 0)
            val amount = BigDecimal.valueOf(priceMinorUnits).movePointLeft(fractionDigits)
            NumberFormat.getCurrencyInstance(locale).apply {
                this.currency = currency
                minimumFractionDigits = fractionDigits
                maximumFractionDigits = fractionDigits
            }.format(amount)
        }.getOrNull()
    }
}
