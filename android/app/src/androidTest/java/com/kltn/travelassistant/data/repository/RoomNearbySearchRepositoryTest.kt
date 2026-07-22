package com.kltn.travelassistant.data.repository

import android.content.Context
import androidx.room.Room
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.kltn.travelassistant.data.local.TravelAssistantDatabase
import com.kltn.travelassistant.data.local.entity.LocalPoiEntity
import com.kltn.travelassistant.data.seed.BundledHcmcSeedSource
import com.kltn.travelassistant.data.seed.RoomCuratedSeedImporter
import com.kltn.travelassistant.data.seed.SeedDocumentParser
import com.kltn.travelassistant.data.seed.SeedImportResult
import com.kltn.travelassistant.data.seed.SeedValidator
import com.kltn.travelassistant.feature.nearby.domain.NearbyPoi
import com.kltn.travelassistant.feature.nearby.domain.NearbySearchResult
import kotlinx.coroutines.test.runTest
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class RoomNearbySearchRepositoryTest {
    private lateinit var database: TravelAssistantDatabase
    private lateinit var repository: RoomNearbySearchRepository

    @Before
    fun setUp() = runTest {
        val context = ApplicationProvider.getApplicationContext<Context>()
        database = Room.inMemoryDatabaseBuilder(
            context,
            TravelAssistantDatabase::class.java,
        ).build()
        val parser = SeedDocumentParser()
        val importResult = RoomCuratedSeedImporter(
            source = BundledHcmcSeedSource(context),
            parser = parser,
            validator = SeedValidator(parser),
            database = database,
        ).importSeed()
        assertTrue(importResult is SeedImportResult.Imported)
        repository = RoomNearbySearchRepository(database.poiContentDao())
    }

    @After
    fun tearDown() {
        database.close()
    }

    @Test
    fun blankQueryReturnsAllFiveBundledPoisSortedByDistance() = runTest {
        val pois = successfulPois(repository.search(BEN_THANH_LATITUDE, BEN_THANH_LONGITUDE, ""))

        assertEquals(5, pois.size)
        assertEquals("hcmc-poi-ben-thanh-market", pois.first().poiId)
        assertTrue(pois.zipWithNext().all { (first, second) ->
            first.distanceMeters <= second.distanceMeters
        })
    }

    @Test
    fun canonicalAliasStoredCategoryAndLocalizedCategoryQueriesMatch() = runTest {
        assertEquals(
            listOf("hcmc-poi-ben-thanh-market"),
            searchIds("cho ben thanh"),
        )
        assertEquals(
            listOf("hcmc-poi-ben-thanh-market"),
            searchIds("ben thanh"),
        )
        assertEquals(
            listOf("hcmc-poi-independence-palace"),
            searchIds("Independence Palace"),
        )
        assertEquals(
            listOf("hcmc-poi-war-remnants-museum"),
            searchIds("museum"),
        )
        assertEquals(
            listOf("hcmc-poi-war-remnants-museum"),
            searchIds("bao tang"),
        )
    }

    @Test
    fun noMatchReturnsEmptyWithoutSynthesizingResults() = runTest {
        assertEquals(emptyList<String>(), searchIds("khong ton tai"))
    }

    @Test
    fun invalidStoredCoordinatesAreExcludedWithoutCrashing() = runTest {
        database.poiContentDao().upsertPois(
            listOf(
                LocalPoiEntity(
                    poiId = "invalid-coordinate",
                    name = "Invalid coordinate",
                    city = RoomNearbySearchRepository.HO_CHI_MINH_CITY,
                    area = null,
                    category = "unknown_category",
                    latitude = 91.0,
                    longitude = 106.0,
                    address = null,
                    shortDescription = null,
                    status = "test",
                    updatedAtEpochMillis = 1,
                ),
            ),
        )

        val pois = successfulPois(repository.search(BEN_THANH_LATITUDE, BEN_THANH_LONGITUDE, ""))

        assertEquals(5, pois.size)
        assertTrue(pois.none { poi -> poi.poiId == "invalid-coordinate" })
    }

    @Test
    fun invalidUserCoordinatesAndDatabaseFailuresAreControlled() = runTest {
        assertEquals(
            NearbySearchResult.InvalidLocation,
            repository.search(91.0, BEN_THANH_LONGITUDE, ""),
        )

        database.openHelper.writableDatabase.execSQL("DROP TABLE local_pois")
        assertEquals(
            NearbySearchResult.DatabaseError,
            repository.search(BEN_THANH_LATITUDE, BEN_THANH_LONGITUDE, ""),
        )
    }

    private suspend fun searchIds(query: String): List<String> = successfulPois(
        repository.search(BEN_THANH_LATITUDE, BEN_THANH_LONGITUDE, query),
    ).map(NearbyPoi::poiId)

    private fun successfulPois(result: NearbySearchResult): List<NearbyPoi> =
        (result as NearbySearchResult.Success).pois

    private companion object {
        const val BEN_THANH_LATITUDE = 10.7725
        const val BEN_THANH_LONGITUDE = 106.6980
    }
}
