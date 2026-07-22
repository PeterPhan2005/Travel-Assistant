package com.kltn.travelassistant.feature.nearby.domain

import java.text.Normalizer
import java.util.Locale

object VietnameseTextNormalizer {
    private val combiningMarks = Regex("\\p{M}+")
    private val repeatedWhitespace = Regex("\\s+")

    fun normalize(value: String): String = Normalizer.normalize(
        value.trim().lowercase(Locale.ROOT),
        Normalizer.Form.NFD,
    )
        .replace(combiningMarks, "")
        .replace('đ', 'd')
        .replace(repeatedWhitespace, " ")
}
