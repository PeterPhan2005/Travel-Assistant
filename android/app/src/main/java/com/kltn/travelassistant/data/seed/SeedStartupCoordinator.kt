package com.kltn.travelassistant.data.seed

import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class SeedStartupCoordinator @Inject constructor(
    private val importer: CuratedSeedImporter,
) {
    suspend fun initialize(): SeedImportResult = importer.importSeed()
}
