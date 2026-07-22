package com.kltn.travelassistant.feature.nearby.domain

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class VietnameseTextNormalizerTest {
    @Test
    fun removesAccentsAndConvertsVietnameseD() {
        assertEquals("cho ben thanh", VietnameseTextNormalizer.normalize("Chợ Bến Thành"))
        assertEquals("dinh doc lap", VietnameseTextNormalizer.normalize("Dinh Độc Lập"))
    }

    @Test
    fun ignoresCaseAndNormalizesWhitespace() {
        assertEquals(
            "ben thanh",
            VietnameseTextNormalizer.normalize("  BẾN\t\nTHÀNH  "),
        )
    }

    @Test
    fun normalizedVietnameseNamesContainUnaccentedQueries() {
        assertTrue(
            VietnameseTextNormalizer.normalize("Bến Thành")
                .contains(VietnameseTextNormalizer.normalize("ben thanh")),
        )
        assertTrue(
            VietnameseTextNormalizer.normalize("Chợ Bến Thành")
                .contains(VietnameseTextNormalizer.normalize("cho ben thanh")),
        )
    }

    @Test
    fun categoryLabelsUseKnownVietnameseLabelsAndSafeFallback() {
        assertEquals(PoiCategoryLabel.MUSEUM, PoiCategoryLabels.labelFor("museum"))
        assertEquals("Bảo tàng", PoiCategoryLabels.searchTextFor(PoiCategoryLabel.MUSEUM))
        assertEquals(PoiCategoryLabel.OTHER, PoiCategoryLabels.labelFor("unsupported"))
        assertEquals("Khác", PoiCategoryLabels.searchTextFor(PoiCategoryLabel.OTHER))
    }
}
