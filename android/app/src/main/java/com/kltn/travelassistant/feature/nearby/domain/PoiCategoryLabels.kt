package com.kltn.travelassistant.feature.nearby.domain

object PoiCategoryLabels {
    private val knownLabels = mapOf(
        "landmark" to PoiCategoryLabel.LANDMARK,
        "market" to PoiCategoryLabel.MARKET,
        "museum" to PoiCategoryLabel.MUSEUM,
        "public_space" to PoiCategoryLabel.PUBLIC_SPACE,
    )

    fun labelFor(category: String): PoiCategoryLabel =
        knownLabels[VietnameseTextNormalizer.normalize(category)] ?: PoiCategoryLabel.OTHER

    fun searchTextFor(label: PoiCategoryLabel): String = when (label) {
        PoiCategoryLabel.LANDMARK -> "Điểm tham quan"
        PoiCategoryLabel.MARKET -> "Chợ"
        PoiCategoryLabel.MUSEUM -> "Bảo tàng"
        PoiCategoryLabel.PUBLIC_SPACE -> "Không gian công cộng"
        PoiCategoryLabel.OTHER -> "Khác"
    }
}

enum class PoiCategoryLabel {
    LANDMARK,
    MARKET,
    MUSEUM,
    PUBLIC_SPACE,
    OTHER,
}
