package com.kltn.travelassistant.data.local

import android.content.Context
import androidx.room.Room
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.kltn.travelassistant.data.local.entity.LocalCultureEntity
import com.kltn.travelassistant.data.local.entity.LocalItineraryEntity
import com.kltn.travelassistant.data.local.entity.LocalItineraryItemEntity
import com.kltn.travelassistant.data.local.entity.LocalMenuItemEntity
import com.kltn.travelassistant.data.local.entity.LocalNarrationEntity
import com.kltn.travelassistant.data.local.entity.LocalPoiAliasEntity
import com.kltn.travelassistant.data.local.entity.LocalPoiEntity
import com.kltn.travelassistant.data.local.entity.PendingSyncOperationEntity
import com.kltn.travelassistant.data.local.entity.TravelPackageEntity
import kotlinx.coroutines.test.runTest
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class TravelAssistantDatabaseTest {
    private lateinit var database: TravelAssistantDatabase

    @Before
    fun setUp() {
        val context = ApplicationProvider.getApplicationContext<Context>()
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
    fun poiAndRelatedContentCanBeInsertedAndRetrieved() = runTest {
        val poi = samplePoi()
        val alias = LocalPoiAliasEntity(
            aliasId = "alias-1",
            poiId = poi.poiId,
            alias = "Bưu điện Sài Gòn",
            normalizedAlias = "buu dien sai gon",
            languageCode = "vi",
        )
        val menuItem = LocalMenuItemEntity(
            menuItemId = "menu-1",
            poiId = poi.poiId,
            dishName = "Cà phê sữa",
            priceMinorUnits = 45_000,
            currencyCode = "VND",
            sourceType = "curated",
            updatedAtEpochMillis = 1_721_510_400_000,
        )
        val narration = LocalNarrationEntity(
            narrationId = "narration-1",
            poiId = poi.poiId,
            languageCode = "vi",
            content = "Nội dung thuyết minh đã xác minh.",
            verificationStatus = "verified",
            generatedAtEpochMillis = 1_721_510_400_000,
        )
        val culture = LocalCultureEntity(
            cultureItemId = "culture-1",
            city = poi.city,
            area = poi.area,
            topic = "Ứng xử",
            content = "Nội dung văn hóa địa phương.",
            verificationStatus = "verified",
        )

        database.poiContentDao().apply {
            upsertPois(listOf(poi))
            upsertAliases(listOf(alias))
            upsertMenuItems(listOf(menuItem))
            upsertNarrations(listOf(narration))
            upsertCultureItems(listOf(culture))
        }

        assertEquals(poi, database.poiContentDao().getPoiById(poi.poiId))
        assertEquals(listOf(poi), database.poiContentDao().getPoisByCity(poi.city))
        assertEquals(listOf(alias), database.poiContentDao().getAliasesForPoi(poi.poiId))
        assertEquals(listOf(menuItem), database.poiContentDao().getMenuItemsForPoi(poi.poiId))
        assertEquals(narration, database.poiContentDao().getNarration(poi.poiId, "vi"))
        assertEquals(listOf(culture), database.poiContentDao().getCultureByCity(poi.city))
        assertEquals(listOf(culture), database.poiContentDao().getCultureByArea(poi.area!!))
    }

    @Test
    fun deletingPoiCascadesOwnedContentButPreservesItineraryItem() = runTest {
        val poi = samplePoi()
        val itinerary = sampleItinerary()
        val item = sampleItineraryItem(
            itemId = "item-1",
            itineraryId = itinerary.itineraryId,
            poiId = poi.poiId,
            position = 0,
        )
        database.poiContentDao().upsertPois(listOf(poi))
        database.poiContentDao().upsertAliases(
            listOf(
                LocalPoiAliasEntity(
                    aliasId = "alias-1",
                    poiId = poi.poiId,
                    alias = "Bưu điện Sài Gòn",
                    normalizedAlias = "buu dien sai gon",
                    languageCode = "vi",
                ),
            ),
        )
        database.itineraryDao().upsertItinerary(itinerary)
        database.itineraryDao().upsertItineraryItems(listOf(item))

        assertEquals(1, database.poiContentDao().deletePoi(poi.poiId))

        assertEquals(emptyList<LocalPoiAliasEntity>(), database.poiContentDao().getAliasesForPoi(poi.poiId))
        assertNull(database.itineraryDao().getItemsForItinerary(itinerary.itineraryId).single().poiId)
    }

    @Test
    fun itineraryItemsUseStableOrderAndCascadeWhenItineraryIsDeleted() = runTest {
        val itinerary = sampleItinerary()
        val items = listOf(
            sampleItineraryItem("item-c", itinerary.itineraryId, null, 2),
            sampleItineraryItem("item-a", itinerary.itineraryId, null, 0),
            sampleItineraryItem("item-b", itinerary.itineraryId, null, 1),
        )
        database.itineraryDao().upsertItinerary(itinerary)
        database.itineraryDao().upsertItineraryItems(items)

        val aggregate = database.itineraryDao().getItineraryWithItems(itinerary.itineraryId)

        assertEquals(itinerary, aggregate?.itinerary)
        assertEquals(listOf(0, 1, 2), aggregate?.items?.map { it.position })
        assertEquals(1, database.itineraryDao().deleteItinerary(itinerary.itineraryId))
        assertEquals(emptyList<LocalItineraryItemEntity>(), database.itineraryDao().getItemsForItinerary(itinerary.itineraryId))
    }

    @Test
    fun packageMetadataIsRetrievedByCityAndVersion() = runTest {
        val travelPackage = TravelPackageEntity(
            packageId = "package-hcmc-1",
            city = "Ho Chi Minh City",
            version = "2026.07.1",
            manifestJson = "{\"version\":\"2026.07.1\"}",
            publishedAtEpochMillis = 1_721_510_400_000,
        )

        database.travelPackageDao().upsertPackage(travelPackage)

        assertEquals(
            travelPackage,
            database.travelPackageDao().getPackage(travelPackage.city, travelPackage.version),
        )
        assertNull(database.travelPackageDao().getPackage(travelPackage.city, "missing"))
    }

    @Test
    fun pendingSyncOperationsHaveDeterministicOrderAndMutableState() = runTest {
        val operations = listOf(
            sampleSyncOperation("operation-c", 200),
            sampleSyncOperation("operation-b", 100),
            sampleSyncOperation("operation-a", 100),
        )
        operations.forEach { database.pendingSyncDao().enqueue(it) }

        assertEquals(
            listOf("operation-a", "operation-b", "operation-c"),
            database.pendingSyncDao().getOperationsByStatus("pending").map { it.operationId },
        )

        assertEquals(1, database.pendingSyncDao().updateStatus("operation-a", "completed", 300))
        assertEquals(
            listOf("operation-b", "operation-c"),
            database.pendingSyncDao().getOperationsByStatus("pending").map { it.operationId },
        )
        assertEquals(1, database.pendingSyncDao().getOperationById("operation-a")?.attemptCount)
        assertEquals(1, database.pendingSyncDao().remove("operation-a"))
        assertNull(database.pendingSyncDao().getOperationById("operation-a"))
    }

    @Test
    fun eachTestUsesAnIsolatedEmptyDatabase() = runTest {
        assertNull(database.poiContentDao().getPoiById("poi-1"))
        assertNull(database.itineraryDao().getItineraryWithItems("itinerary-1"))
        assertEquals(emptyList<PendingSyncOperationEntity>(), database.pendingSyncDao().getOperationsByStatus("pending"))
    }

    private fun samplePoi() = LocalPoiEntity(
        poiId = "poi-1",
        name = "Bưu điện Trung tâm Sài Gòn",
        city = "Ho Chi Minh City",
        area = "District 1",
        category = "landmark",
        latitude = 10.779_783,
        longitude = 106.699_018,
        address = "2 Công xã Paris",
        shortDescription = "Bưu điện lịch sử ở trung tâm thành phố.",
        status = "active",
        updatedAtEpochMillis = 1_721_510_400_000,
    )

    private fun sampleItinerary() = LocalItineraryEntity(
        itineraryId = "itinerary-1",
        title = "Một ngày ở Quận 1",
        createdAtEpochMillis = 100,
        updatedAtEpochMillis = 100,
    )

    private fun sampleItineraryItem(
        itemId: String,
        itineraryId: String,
        poiId: String?,
        position: Int,
    ) = LocalItineraryItemEntity(
        itineraryItemId = itemId,
        itineraryId = itineraryId,
        poiId = poiId,
        title = "Điểm dừng $position",
        position = position,
        startAtEpochMillis = null,
        endAtEpochMillis = null,
        travelTimeMinutes = null,
        notes = null,
    )

    private fun sampleSyncOperation(
        operationId: String,
        createdAtEpochMillis: Long,
    ) = PendingSyncOperationEntity(
        operationId = operationId,
        operationType = "upsert",
        entityType = "itinerary",
        entityId = "itinerary-1",
        payloadJson = "{}",
        status = "pending",
        createdAtEpochMillis = createdAtEpochMillis,
        lastAttemptAtEpochMillis = null,
        attemptCount = 0,
    )
}
