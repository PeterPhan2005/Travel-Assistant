package com.kltn.travelassistant.feature.nearby.presentation

import androidx.annotation.StringRes
import com.kltn.travelassistant.R
import com.kltn.travelassistant.feature.nearby.domain.PoiCategoryLabel

@get:StringRes
val PoiCategoryLabel.labelRes: Int
    get() = when (this) {
        PoiCategoryLabel.LANDMARK -> R.string.nearby_category_landmark
        PoiCategoryLabel.MARKET -> R.string.nearby_category_market
        PoiCategoryLabel.MUSEUM -> R.string.nearby_category_museum
        PoiCategoryLabel.PUBLIC_SPACE -> R.string.nearby_category_public_space
        PoiCategoryLabel.OTHER -> R.string.nearby_category_other
    }
