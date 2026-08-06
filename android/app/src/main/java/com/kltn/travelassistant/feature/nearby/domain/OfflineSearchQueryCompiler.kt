package com.kltn.travelassistant.feature.nearby.domain

sealed interface CompiledOfflineSearchQuery {
    data object Blank : CompiledOfflineSearchQuery

    data object NoSearchableTerms : CompiledOfflineSearchQuery

    data class Match(val expression: String) : CompiledOfflineSearchQuery
}

/** Compiles user text into application-owned FTS syntax without accepting raw MATCH operators. */
object OfflineSearchQueryCompiler {
    private val searchableToken = Regex("[\\p{L}\\p{N}]+")

    fun compile(query: String): CompiledOfflineSearchQuery {
        if (query.isBlank()) return CompiledOfflineSearchQuery.Blank

        val normalized = VietnameseTextNormalizer.normalize(query)
        val terms = searchableToken.findAll(normalized).map { match -> match.value }.toList()
        if (terms.isEmpty()) return CompiledOfflineSearchQuery.NoSearchableTerms

        return CompiledOfflineSearchQuery.Match(
            expression = terms.joinToString(separator = " ") { term -> "\"$term*\"" },
        )
    }
}
