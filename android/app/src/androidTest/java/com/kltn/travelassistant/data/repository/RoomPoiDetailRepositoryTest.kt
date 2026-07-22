package com.kltn.travelassistant.data.repository

import android.content.Context
import androidx.room.Room
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.kltn.travelassistant.data.local.TravelAssistantDatabase
import com.kltn.travelassistant.data.local.dao.PoiContentDao
import com.kltn.travelassistant.data.local.entity.LocalMenuItemEntity
import com.kltn.travelassistant.data.local.entity.LocalNarrationEntity
import com.kltn.travelassistant.data.local.entity.LocalPoiEntity
import com.kltn.travelassistant.feature.nearby.domain.PoiCategoryLabel
import com.kltn.travelassistant.feature.poi.domain.PoiDetailResult
import java.lang.reflect.Proxy
import kotlinx.coroutines.test.runTest
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class RoomPoiDetailRepositoryTest {
    private lateinit var database: TravelAssistantDatabase
    private lateinit var repository: RoomPoiDetailRepository

    @Before
    fun setUp() {
        database = Room.inMemoryDatabaseBuilder(
            ApplicationProvider.getApplicationContext<Context>(),
            TravelAssistantDatabase::class.java,
        ).build()
        repository = RoomPoiDetailRepository(database.poiContentDao())
    }

    @After
    fun tearDown() {
        if (database.isOpen) database.close()
    }

    @Test
    fun existingPoiPreservesOptionalAbsenceMenuFreshnessAndSourcedNarration() = runTest {
        val poi = samplePoi()
        val menu = LocalMenuItemEntity(
            menuItemId = "menu-1",
            poiId = poi.poiId,
            dishName = "Cà phê sữa",
            priceMinorUnits = 45_000,
            currencyCode = "VND",
            sourceType = "curated_menu",
            updatedAtEpochMillis = 1_721_510_400_000,
        )
        val narration = LocalNarrationEntity(
            narrationId = "narration-1",
            poiId = poi.poiId,
            languageCode = "vi",
            content = "Nội dung thuyết minh đã lưu.",
            verificationStatus = "verified",
            generatedAtEpochMillis = 1_721_510_400_000,
            sourceLabel = "Ban quản lý điểm đến",
        )
        database.poiContentDao().apply {
            upsertPois(listOf(poi))
            upsertMenuItems(listOf(menu))
            upsertNarrations(listOf(narration))
        }

        val result = repository.getPoiDetail(poi.poiId, "vi") as PoiDetailResult.Success

        assertEquals(poi.poiId, result.detail.poiId)
        assertEquals(PoiCategoryLabel.LANDMARK, result.detail.category)
        assertNull(result.detail.area)
        assertNull(result.detail.address)
        assertNull(result.detail.shortDescription)
        assertEquals("Cà phê sữa", result.detail.menuItems.single().dishName)
        assertEquals(45_000, result.detail.menuItems.single().priceMinorUnits)
        assertEquals("VND", result.detail.menuItems.single().currencyCode)
        assertEquals("curated_menu", result.detail.menuItems.single().sourceType)
        assertEquals(1_721_510_400_000, result.detail.menuItems.single().updatedAtEpochMillis)
        assertEquals("Nội dung thuyết minh đã lưu.", result.detail.narration?.content)
        assertEquals("Ban quản lý điểm đến", result.detail.narration?.sourceLabel)
    }

    @Test
    fun narrationWithoutRealSourceLabelIsNotExposed() = runTest {
        val poi = samplePoi()
        database.poiContentDao().apply {
            upsertPois(listOf(poi))
            upsertNarrations(
                listOf(
                    LocalNarrationEntity(
                        narrationId = "narration-1",
                        poiId = poi.poiId,
                        languageCode = "vi",
                        content = "Không được hiển thị như nội dung có nguồn.",
                        verificationStatus = "verified",
                        generatedAtEpochMillis = 1,
                        sourceLabel = null,
                    ),
                ),
            )
        }

        val result = repository.getPoiDetail(poi.poiId, "vi") as PoiDetailResult.Success

        assertNull(result.detail.narration)

        database.poiContentDao().upsertNarrations(
            listOf(
                LocalNarrationEntity(
                    narrationId = "narration-1",
                    poiId = poi.poiId,
                    languageCode = "vi",
                    content = "Vẫn không được hiển thị như nội dung có nguồn.",
                    verificationStatus = "verified",
                    generatedAtEpochMillis = 1,
                    sourceLabel = " ",
                ),
            ),
        )

        val blankSourceResult = repository.getPoiDetail(
            poi.poiId,
            "vi",
        ) as PoiDetailResult.Success
        assertNull(blankSourceResult.detail.narration)
    }

    @Test
    fun missingPoiReturnsNotFound() = runTest {
        assertEquals(PoiDetailResult.NotFound, repository.getPoiDetail("missing", "vi"))
    }

    @Test
    fun databaseFailureReturnsControlledError() = runTest {
        val failingDao = Proxy.newProxyInstance(
            PoiContentDao::class.java.classLoader,
            arrayOf(PoiContentDao::class.java),
        ) { _, _, _ -> throw IllegalStateException("Controlled database failure") } as PoiContentDao
        val failingRepository = RoomPoiDetailRepository(failingDao)

        assertEquals(PoiDetailResult.DatabaseError, failingRepository.getPoiDetail("poi-1", "vi"))
    }

    private fun samplePoi() = LocalPoiEntity(
        poiId = "poi-1",
        name = "Bưu điện Trung tâm Sài Gòn",
        city = "Ho Chi Minh City",
        area = null,
        category = "landmark",
        latitude = 10.7799,
        longitude = 106.7,
        address = null,
        shortDescription = null,
        status = "active",
        updatedAtEpochMillis = 1_721_510_400_000,
    )
}
