package com.kltn.travelassistant.data.packages

import android.content.Context
import androidx.room.Room
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.kltn.travelassistant.data.local.TravelAssistantDatabase
import com.kltn.travelassistant.data.local.entity.LocalItineraryEntity
import com.kltn.travelassistant.data.local.entity.LocalItineraryItemEntity
import com.kltn.travelassistant.data.local.entity.LocalMenuItemEntity
import com.kltn.travelassistant.data.local.entity.LocalPoiAliasEntity
import com.kltn.travelassistant.data.local.entity.LocalPoiEntity
import com.kltn.travelassistant.data.repository.RoomNearbySearchRepository
import com.kltn.travelassistant.data.seed.BundledHcmcSeedSource
import com.kltn.travelassistant.data.seed.RoomCuratedSeedImporter
import com.kltn.travelassistant.data.seed.SeedDocumentParser
import com.kltn.travelassistant.data.seed.SeedImportResult
import com.kltn.travelassistant.data.seed.SeedValidator
import com.kltn.travelassistant.feature.downloads.domain.PackageCity
import com.kltn.travelassistant.feature.nearby.domain.NearbyPoi
import com.kltn.travelassistant.feature.nearby.domain.NearbySearchResult
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.test.runTest
import okhttp3.HttpUrl.Companion.toHttpUrl
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class RoomPackageActivatorTest {
    private lateinit var context: Context
    private lateinit var database: TravelAssistantDatabase
    private lateinit var activator: RoomPackageActivator

    @Before
    fun setUp() {
        context = ApplicationProvider.getApplicationContext()
        database = Room.inMemoryDatabaseBuilder(
            context,
            TravelAssistantDatabase::class.java,
        ).build()
        activator = RoomPackageActivator(database)
    }

    @After
    fun tearDown() {
        database.close()
    }

    @Test
    fun downloadedPackageAtomicallyReplacesBundleAndSeedCannotOverwriteOnRestart() = runTest {
        val importer = seedImporter()
        assertEquals(SeedImportResult.Imported::class, importer.importSeed()::class)
        assertEquals(5, hcmcPois().size)

        assertEquals(
            PackageActivationResult.ACTIVATED,
            activator.activate(validatedPackage()),
        )

        assertEquals(
            listOf(
                "hcmc-poi-central-post-office",
                "hcmc-poi-war-remnants-museum",
            ),
            hcmcPois().map(LocalPoiEntity::poiId),
        )
        val active = database.travelPackageDao()
            .observeLatestPackage(PackageCity.HCMC.displayName)
            .first()
        assertEquals("hcmc-starter-v1", active?.packageId)
        assertEquals("1.0.0", active?.version)
        assertEquals(SeedImportResult.AlreadyImported, seedImporter().importSeed())
        assertEquals(2, hcmcPois().size)
        assertEquals("hcmc-starter-v1", database.travelPackageDao()
            .getLatestPackage(PackageCity.HCMC.displayName)?.packageId)
    }

    @Test
    fun replacementAtomicallyRemovesOldIndexAndSearchesNewAliasAndDish() = runTest {
        seedImporter().importSeed()
        val postOfficeId = "hcmc-poi-central-post-office"
        val replacement = validatedPackage().copy(
            aliases = listOf(
                LocalPoiAliasEntity(
                    aliasId = "hcmc-alias-new-post-office",
                    poiId = postOfficeId,
                    alias = "Bưu điện mới",
                    normalizedAlias = "buu dien moi",
                    languageCode = "vi",
                ),
            ),
            menuItems = listOf(
                LocalMenuItemEntity(
                    menuItemId = "hcmc-menu-new-coffee",
                    poiId = postOfficeId,
                    dishName = "Cà phê sữa đá",
                    priceMinorUnits = 45_000,
                    currencyCode = "VND",
                    sourceType = "official_operator",
                    updatedAtEpochMillis = 1_785_085_200_000,
                ),
            ),
        )

        assertEquals(PackageActivationResult.ACTIVATED, activator.activate(replacement))

        val repository = RoomNearbySearchRepository(database.poiContentDao())
        assertEquals(listOf(postOfficeId), searchIds(repository, "buu dien moi"))
        assertEquals(listOf(postOfficeId), searchIds(repository, "ca phe sua da"))
        assertEquals(emptyList<String>(), searchIds(repository, "Independence Palace"))
    }

    @Test
    fun activationPreservesUnrelatedCityAndUserItineraryItem() = runTest {
        seedImporter().importSeed()
        val staleHcmcPoiId = "hcmc-poi-independence-palace"
        database.poiContentDao().upsertPois(listOf(bangkokPoi()))
        database.itineraryDao().upsertItinerary(
            LocalItineraryEntity(
                itineraryId = "trip-1",
                title = "Ngày ở Sài Gòn",
                accountKey = "account-a",
                city = "hcmc",
                localDate = "2026-08-01",
                timezone = "Asia/Ho_Chi_Minh",
                startLocalTime = "09:00",
                endLocalTime = "17:00",
                assumptionsJson = "[\"Giữ lịch trình cục bộ\"]",
                warningsJson = "[]",
                localRevision = 1,
                serverRevision = 0,
                syncState = "pending",
                isDeleted = false,
                createdAtEpochMillis = 1,
                updatedAtEpochMillis = 1,
            ),
        )
        database.itineraryDao().upsertItineraryItems(
            listOf(
                LocalItineraryItemEntity(
                    itineraryItemId = "trip-item-1",
                    itineraryId = "trip-1",
                    poiId = staleHcmcPoiId,
                    title = "Dinh Độc Lập",
                    position = 0,
                    startAtEpochMillis = null,
                    endAtEpochMillis = null,
                    travelTimeMinutes = null,
                    notes = "Giữ mục người dùng",
                ),
            ),
        )

        activator.activate(validatedPackage())

        assertNotNull(database.poiContentDao().getPoiById("bkk-poi-temple"))
        val itinerary = database.itineraryDao().getItineraryWithItems("account-a", "trip-1")
        assertNotNull(itinerary)
        assertEquals("Dinh Độc Lập", itinerary?.items?.single()?.title)
        assertNull(itinerary?.items?.single()?.poiId)
    }

    @Test
    fun lateMetadataFailureRollsBackAllDeletesAndInserts() = runTest {
        seedImporter().importSeed()
        val beforePois = hcmcPois()
        val beforePackage = database.travelPackageDao()
            .getLatestPackage(PackageCity.HCMC.displayName)
        database.openHelper.writableDatabase.execSQL(
            """
            CREATE TRIGGER reject_downloaded_package
            BEFORE INSERT ON travel_packages
            WHEN NEW.package_id = 'hcmc-starter-v1'
            BEGIN
                SELECT RAISE(ABORT, 'test activation failure');
            END
            """.trimIndent(),
        )

        try {
            activator.activate(validatedPackage())
            throw AssertionError("Expected activation failure")
        } catch (_: Exception) {
            // Expected trigger failure.
        }

        assertEquals(beforePois, hcmcPois())
        assertEquals(
            beforePackage,
            database.travelPackageDao().getLatestPackage(PackageCity.HCMC.displayName),
        )
    }

    @Test
    fun repeatedSameVersionIsIdempotentAndOlderPackageIsRejected() = runTest {
        val current = validatedPackage()
        assertEquals(PackageActivationResult.ACTIVATED, activator.activate(current))
        assertEquals(PackageActivationResult.ALREADY_ACTIVE, activator.activate(current))

        val older = current.copy(
            metadata = current.metadata.copy(
                version = "0.9.0",
                publishedAtEpochMillis = current.metadata.publishedAtEpochMillis - 1,
                manifestJson = current.metadata.manifestJson.replace("1.0.0", "0.9.0"),
            ),
        )
        assertEquals(
            PackageActivationResult.REJECTED_OLDER_OR_CONFLICTING,
            activator.activate(older),
        )
        assertEquals("1.0.0", database.travelPackageDao()
            .getLatestPackage(PackageCity.HCMC.displayName)?.version)
        assertEquals(2, hcmcPois().size)
    }

    private fun validatedPackage(): ValidatedTravelPackage {
        val rawManifest =
            """{"artifactSchemaVersion":1,"byteSize":934,"city":"hcmc","contentVersion":"1.0.0","dataFilename":"hcmc-starter-v1-1.0.0.data.json","mediaType":"application/json","packageId":"hcmc-starter-v1","publishedAt":"2026-07-26T17:00:00Z","schemaVersion":1,"sha256":"daa7678e1998348c6904f12f6e96026aa7ac33068fab7d8dcdc2ec0b23ae6be3"}"""
        val manifest = PackageManifestValidator().validate(
            PackageManifestParser().parse(rawManifest),
            rawManifest,
            PackageManifestLocation(
                PackageCity.HCMC,
                "https://packages.example.test/manifest.json".toHttpUrl(),
            ),
        )
        val poiIds = listOf(
            "hcmc-poi-central-post-office",
            "hcmc-poi-war-remnants-museum",
        )
        val artifact = PackageArtifactDocument(
            formatVersion = 1,
            packageMetadata = PackageArtifactMetadata(
                packageId = "hcmc-starter-v1",
                city = PackageCity.HCMC.displayName,
                version = "1.0.0",
                publishedAtEpochMillis = 1_785_085_200_000,
                manifest = PackageArtifactPoiManifest(1, poiIds),
            ),
            pois = listOf(
                packagePoi(
                    id = poiIds[0],
                    name = "Bưu điện Trung tâm Sài Gòn",
                    latitude = 10.7799,
                    longitude = 106.7,
                ),
                packagePoi(
                    id = poiIds[1],
                    name = "Bảo tàng Chứng tích Chiến tranh",
                    latitude = 10.7795,
                    longitude = 106.692,
                ),
            ),
        )
        return PackageArtifactValidator().validate(artifact, manifest)
    }

    private fun packagePoi(
        id: String,
        name: String,
        latitude: Double,
        longitude: Double,
    ) = PackageArtifactPoi(
        poiId = id,
        name = name,
        city = PackageCity.HCMC.displayName,
        category = "landmark",
        latitude = latitude,
        longitude = longitude,
        status = "curated",
        updatedAtEpochMillis = 1_785_085_200_000,
    )

    private fun seedImporter(): RoomCuratedSeedImporter {
        val parser = SeedDocumentParser()
        return RoomCuratedSeedImporter(
            source = BundledHcmcSeedSource(context),
            parser = parser,
            validator = SeedValidator(parser),
            database = database,
        )
    }

    private suspend fun hcmcPois(): List<LocalPoiEntity> =
        database.poiContentDao().getPoisByCity(PackageCity.HCMC.displayName)

    private suspend fun searchIds(
        repository: RoomNearbySearchRepository,
        query: String,
    ): List<String> = (
        repository.search(
            latitude = 10.7799,
            longitude = 106.7,
            query = query,
        ) as NearbySearchResult.Success
        ).pois.map(NearbyPoi::poiId)

    private fun bangkokPoi() = LocalPoiEntity(
        poiId = "bkk-poi-temple",
        name = "Temple",
        city = "Bangkok",
        area = null,
        category = "landmark",
        latitude = 13.75,
        longitude = 100.5,
        address = null,
        shortDescription = null,
        status = "curated",
        updatedAtEpochMillis = 1,
    )
}
