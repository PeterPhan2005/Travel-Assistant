package com.kltn.travelassistant.data.seed

import android.content.Context
import androidx.room.Room
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.kltn.travelassistant.data.local.TravelAssistantDatabase
import com.kltn.travelassistant.data.local.entity.LocalPoiEntity
import kotlinx.coroutines.test.runTest
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class CuratedSeedImporterTest {
    private lateinit var context: Context
    private lateinit var database: TravelAssistantDatabase
    private val parser = SeedDocumentParser()
    private val validator = SeedValidator(parser)

    @Before
    fun setUp() {
        context = ApplicationProvider.getApplicationContext()
        database = Room.inMemoryDatabaseBuilder(
            context,
            TravelAssistantDatabase::class.java,
        ).build()
    }

    @After
    fun tearDown() {
        database.close()
    }

    @Test
    fun bundledAssetParsesImportsAndIsIdempotent() = runTest {
        val rawDocument = bundledSeed()
        val document = parser.parse(rawDocument)
        val poiIds = document.pois.map(SeedPoi::poiId)

        assertTrue(document.pois.size >= SeedValidator.MINIMUM_POI_COUNT)
        assertEquals(poiIds.size, poiIds.toSet().size)
        assertTrue(document.aliases.all { it.poiId in poiIds })

        val importer = importerFor(rawDocument)
        val firstResult = importer.importSeed()
        val firstSnapshot = snapshot()
        val secondResult = importer.importSeed()
        val secondSnapshot = snapshot()

        assertEquals(
            SeedImportResult.Imported(
                SeedRecordCounts(
                    pois = 5,
                    aliases = 5,
                    menuItems = 0,
                    narrations = 0,
                    cultureItems = 0,
                ),
            ),
            firstResult,
        )
        assertEquals(5, firstSnapshot.poiIds.size)
        assertEquals(5, firstSnapshot.aliasIds.size)
        assertEquals(SeedImportResult.AlreadyImported, secondResult)
        assertEquals(firstSnapshot, secondSnapshot)
        val packageMetadata = database.travelPackageDao().getPackageByIdAndVersion(
            packageId = "bundled-hcmc-demo",
            version = "1",
        )
        assertNotNull(packageMetadata)
        assertEquals(SeedValidator.SUPPORTED_CITY, packageMetadata?.city)
        assertEquals(1_784_592_000_000, packageMetadata?.publishedAtEpochMillis)
        assertTrue(packageMetadata?.manifestJson?.contains("hcmc-poi-ben-thanh-market") == true)
    }

    @Test
    fun malformedJsonReturnsFailureAndLeavesExistingDataUnchanged() = runTest {
        val existingPoi = sampleExistingPoi()
        database.poiContentDao().upsertPois(listOf(existingPoi))

        val result = importerFor("{").importSeed()

        assertEquals(
            SeedImportResult.Failed(SeedImportFailure.MALFORMED_DOCUMENT),
            result,
        )
        assertEquals(
            listOf(existingPoi),
            database.poiContentDao().getPoisByCity(SeedValidator.SUPPORTED_CITY),
        )
        assertEquals(
            null,
            database.travelPackageDao().getPackageByIdAndVersion("bundled-hcmc-demo", "1"),
        )
    }

    @Test
    fun invalidChildReferenceFailsBeforeAnyDatabaseWrite() = runTest {
        val invalidDocument = bundledSeed().replace(
            oldValue = """"aliasId": "hcmc-alias-central-post-office-en",
      "poiId": "hcmc-poi-central-post-office"""",
            newValue = """"aliasId": "hcmc-alias-central-post-office-en",
      "poiId": "missing-poi"""",
        )

        val result = importerFor(invalidDocument).importSeed()

        assertEquals(
            SeedImportResult.Failed(SeedImportFailure.INVALID_DOCUMENT),
            result,
        )
        assertEquals(
            emptyList<LocalPoiEntity>(),
            database.poiContentDao().getPoisByCity(SeedValidator.SUPPORTED_CITY),
        )
        assertEquals(
            null,
            database.travelPackageDao().getPackageByIdAndVersion("bundled-hcmc-demo", "1"),
        )
    }

    @Test
    fun databaseFailureRollsBackPoiAndAliasWrites() = runTest {
        database.openHelper.writableDatabase.execSQL(
            """
            CREATE TRIGGER reject_bundled_seed_package
            BEFORE INSERT ON travel_packages
            WHEN NEW.package_id = 'bundled-hcmc-demo'
            BEGIN
                SELECT RAISE(ABORT, 'test package write failure');
            END
            """.trimIndent(),
        )

        val result = importerFor(bundledSeed()).importSeed()

        assertEquals(SeedImportResult.Failed(SeedImportFailure.DATABASE), result)
        assertEquals(
            emptyList<LocalPoiEntity>(),
            database.poiContentDao().getPoisByCity(SeedValidator.SUPPORTED_CITY),
        )
        assertEquals(
            null,
            database.travelPackageDao().getPackageByIdAndVersion("bundled-hcmc-demo", "1"),
        )
    }

    private fun importerFor(rawDocument: String) = RoomCuratedSeedImporter(
        source = SeedSource { rawDocument },
        parser = parser,
        validator = validator,
        database = database,
    )

    private suspend fun bundledSeed(): String = BundledHcmcSeedSource(context).read()

    private suspend fun snapshot(): SeedSnapshot {
        val pois = database.poiContentDao().getPoisByCity(SeedValidator.SUPPORTED_CITY)
        return SeedSnapshot(
            poiIds = pois.map(LocalPoiEntity::poiId),
            aliasIds = pois.flatMap { poi ->
                database.poiContentDao().getAliasesForPoi(poi.poiId)
            }.map { it.aliasId },
        )
    }

    private fun sampleExistingPoi() = LocalPoiEntity(
        poiId = "existing-poi",
        name = "Existing POI",
        city = SeedValidator.SUPPORTED_CITY,
        area = null,
        category = "test",
        latitude = 10.0,
        longitude = 106.0,
        address = null,
        shortDescription = null,
        status = "test",
        updatedAtEpochMillis = 1,
    )

    private data class SeedSnapshot(
        val poiIds: List<String>,
        val aliasIds: List<String>,
    )
}
