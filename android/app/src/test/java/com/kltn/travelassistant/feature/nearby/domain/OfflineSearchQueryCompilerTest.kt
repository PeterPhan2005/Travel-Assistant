package com.kltn.travelassistant.feature.nearby.domain

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Test

class OfflineSearchQueryCompilerTest {
    @Test
    fun blankAndWhitespaceOnlyQueriesRemainBlank() {
        assertEquals(CompiledOfflineSearchQuery.Blank, OfflineSearchQueryCompiler.compile(""))
        assertEquals(
            CompiledOfflineSearchQuery.Blank,
            OfflineSearchQueryCompiler.compile(" \t\n "),
        )
    }

    @Test
    fun VietnameseCaseDiacriticsCombiningMarksAndWhitespaceShareOneConvention() {
        val expected = CompiledOfflineSearchQuery.Match("\"ca*\" \"phe*\" \"sua*\"")

        assertEquals(expected, OfflineSearchQueryCompiler.compile("CÀ   PHÊ SỮA"))
        assertEquals(expected, OfflineSearchQueryCompiler.compile("ca phe sua"))
        assertEquals(expected, OfflineSearchQueryCompiler.compile("ca\u0300 phe\u0302 su\u0303a"))
    }

    @Test
    fun punctuationWildcardsQuotesAndOperatorsNeverBecomeRawMatchSyntax() {
        val compiled = OfflineSearchQueryCompiler.compile(
            "'phở' OR NEAR MATCH %_ \"1=1\"",
        ) as CompiledOfflineSearchQuery.Match

        assertEquals(
            "\"pho*\" \"or*\" \"near*\" \"match*\" \"1*\" \"1*\"",
            compiled.expression,
        )
        assertFalse(compiled.expression.contains('%'))
        assertFalse(compiled.expression.contains('_'))
        assertFalse(compiled.expression.contains("1=1"))
    }

    @Test
    fun punctuationOnlyAndStandaloneCombiningMarksHaveNoSearchableTerms() {
        assertEquals(
            CompiledOfflineSearchQuery.NoSearchableTerms,
            OfflineSearchQueryCompiler.compile("'\"%_-*"),
        )
        assertEquals(
            CompiledOfflineSearchQuery.NoSearchableTerms,
            OfflineSearchQueryCompiler.compile("\u0301\u0300"),
        )
    }

    @Test
    fun longUnicodeInputIsNotTruncatedOrReinterpreted() {
        val term = "đ".repeat(1_000)
        val compiled = OfflineSearchQueryCompiler.compile(term) as CompiledOfflineSearchQuery.Match

        assertEquals("\"${"d".repeat(1_000)}*\"", compiled.expression)
    }
}
