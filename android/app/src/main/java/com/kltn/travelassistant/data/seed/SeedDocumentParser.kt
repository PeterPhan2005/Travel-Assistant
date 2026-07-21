package com.kltn.travelassistant.data.seed

import javax.inject.Inject
import kotlinx.serialization.json.Json

class SeedDocumentParser @Inject constructor() {
    private val json = Json {
        ignoreUnknownKeys = false
        isLenient = false
        coerceInputValues = false
        allowSpecialFloatingPointValues = false
        useAlternativeNames = false
        explicitNulls = true
    }

    fun parse(rawDocument: String): SeedDocument = json.decodeFromString(rawDocument)

    fun encodeManifest(manifest: SeedManifest): String = json.encodeToString(manifest)
}
