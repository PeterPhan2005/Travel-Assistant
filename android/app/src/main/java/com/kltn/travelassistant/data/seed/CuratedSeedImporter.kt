package com.kltn.travelassistant.data.seed

import androidx.room.withTransaction
import com.kltn.travelassistant.data.local.TravelAssistantDatabase
import javax.inject.Inject
import javax.inject.Singleton
import kotlinx.coroutines.CancellationException

sealed interface SeedImportResult {
    data class Imported(val counts: SeedRecordCounts) : SeedImportResult

    data object AlreadyImported : SeedImportResult

    data class Failed(val reason: SeedImportFailure) : SeedImportResult
}

enum class SeedImportFailure {
    SOURCE,
    MALFORMED_DOCUMENT,
    INVALID_DOCUMENT,
    DATABASE,
}

interface CuratedSeedImporter {
    suspend fun importSeed(): SeedImportResult
}

@Singleton
class RoomCuratedSeedImporter @Inject constructor(
    private val source: SeedSource,
    private val parser: SeedDocumentParser,
    private val validator: SeedValidator,
    private val database: TravelAssistantDatabase,
) : CuratedSeedImporter {
    override suspend fun importSeed(): SeedImportResult {
        val rawDocument = try {
            source.read()
        } catch (exception: CancellationException) {
            throw exception
        } catch (_: Exception) {
            return SeedImportResult.Failed(SeedImportFailure.SOURCE)
        }

        val document = try {
            parser.parse(rawDocument)
        } catch (exception: CancellationException) {
            throw exception
        } catch (_: Exception) {
            return SeedImportResult.Failed(SeedImportFailure.MALFORMED_DOCUMENT)
        }

        val seed = try {
            validator.validate(document)
        } catch (exception: CancellationException) {
            throw exception
        } catch (_: Exception) {
            return SeedImportResult.Failed(SeedImportFailure.INVALID_DOCUMENT)
        }

        return try {
            database.withTransaction {
                val metadata = seed.travelPackage
                val existingPackage = database.travelPackageDao().getPackageByIdAndVersion(
                    packageId = metadata.packageId,
                    version = metadata.version,
                )
                if (existingPackage != null) {
                    return@withTransaction SeedImportResult.AlreadyImported
                }

                database.poiContentDao().apply {
                    upsertPois(seed.pois)
                    if (seed.aliases.isNotEmpty()) upsertAliases(seed.aliases)
                    if (seed.menuItems.isNotEmpty()) upsertMenuItems(seed.menuItems)
                    if (seed.narrations.isNotEmpty()) upsertNarrations(seed.narrations)
                    if (seed.cultureItems.isNotEmpty()) upsertCultureItems(seed.cultureItems)
                }
                database.travelPackageDao().upsertPackage(metadata)
                SeedImportResult.Imported(seed.counts)
            }
        } catch (exception: CancellationException) {
            throw exception
        } catch (_: Exception) {
            SeedImportResult.Failed(SeedImportFailure.DATABASE)
        }
    }
}
