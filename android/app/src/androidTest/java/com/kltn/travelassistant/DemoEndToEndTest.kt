package com.kltn.travelassistant

import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performScrollTo
import androidx.compose.ui.test.performTextInput
import androidx.lifecycle.SavedStateHandle
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.room.Room
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.kltn.travelassistant.data.local.TravelAssistantDatabase
import com.kltn.travelassistant.data.local.entity.LocalMenuItemEntity
import com.kltn.travelassistant.data.local.entity.LocalNarrationEntity
import com.kltn.travelassistant.data.location.DeviceLocation
import com.kltn.travelassistant.data.location.LocationAcquisitionResult
import com.kltn.travelassistant.data.location.LocationClient
import com.kltn.travelassistant.data.repository.AppInfoRepository
import com.kltn.travelassistant.data.repository.RoomNearbySearchRepository
import com.kltn.travelassistant.data.repository.RoomPoiDetailRepository
import com.kltn.travelassistant.data.seed.BundledHcmcSeedSource
import com.kltn.travelassistant.data.seed.RoomCuratedSeedImporter
import com.kltn.travelassistant.data.seed.SeedDocumentParser
import com.kltn.travelassistant.data.seed.SeedImportResult
import com.kltn.travelassistant.data.seed.SeedValidator
import com.kltn.travelassistant.feature.appshell.presentation.AppShellUiState
import com.kltn.travelassistant.feature.appshell.presentation.ConnectivityUiState
import com.kltn.travelassistant.feature.appshell.presentation.LocalPackageUiState
import com.kltn.travelassistant.feature.home.domain.DemoLocationPreset
import com.kltn.travelassistant.feature.home.domain.DemoLocationPresetProvider
import com.kltn.travelassistant.feature.home.presentation.HomeViewModel
import com.kltn.travelassistant.feature.home.presentation.NearbySearchUiState
import com.kltn.travelassistant.feature.poi.domain.PoiNavigationTarget
import com.kltn.travelassistant.feature.poi.presentation.PoiDetailScreen
import com.kltn.travelassistant.feature.poi.presentation.PoiDetailViewModel
import com.kltn.travelassistant.navigation.PoiDetailDestination
import java.util.concurrent.atomic.AtomicReference
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.runBlocking
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class DemoEndToEndTest {
    @get:Rule
    val composeRule = createComposeRule()

    private lateinit var database: TravelAssistantDatabase
    private lateinit var homeViewModel: HomeViewModel
    private lateinit var detailRepository: RoomPoiDetailRepository
    private val connectivity = MutableStateFlow(ConnectivityUiState.Online)
    private val openedNavigationTarget = AtomicReference<PoiNavigationTarget?>()

    @Before
    fun setUp() = runBlocking {
        val context = ApplicationProvider.getApplicationContext<android.content.Context>()
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
        database.poiContentDao().apply {
            upsertMenuItems(
                listOf(
                    LocalMenuItemEntity(
                        menuItemId = FOOD_MENU_ITEM_ID,
                        poiId = FOOD_POI_ID,
                        dishName = FOOD_DISH,
                        priceMinorUnits = 75_000,
                        currencyCode = "VND",
                        sourceType = "official_operator",
                        updatedAtEpochMillis = FIXTURE_TIMESTAMP,
                    ),
                ),
            )
            upsertNarrations(
                listOf(
                    LocalNarrationEntity(
                        narrationId = FOOD_NARRATION_ID,
                        poiId = FOOD_POI_ID,
                        languageCode = "vi",
                        content = NARRATION_CONTENT,
                        verificationStatus = "verified",
                        generatedAtEpochMillis = FIXTURE_TIMESTAMP,
                        sourceLabel = NARRATION_SOURCE,
                    ),
                ),
            )
        }
        homeViewModel = HomeViewModel(
            repository = FixedAppInfoRepository(),
            locationClient = FixedHcmcLocationClient(),
            nearbySearchRepository = RoomNearbySearchRepository(database.poiContentDao()),
            demoLocationPresetProvider = object : DemoLocationPresetProvider {
                override val presets: List<DemoLocationPreset> = emptyList()
            },
        )
        detailRepository = RoomPoiDetailRepository(database.poiContentDao())
    }

    @After
    fun tearDown() {
        if (::database.isInitialized && database.isOpen) database.close()
    }

    @Test
    fun hcmcFoodQueryOpensSourcedDetailAndReachesExternalNavigationBoundary() {
        setDemoContent()

        submitFoodQuery(FOOD_QUERY_ACCENTED)
        composeRule.onNodeWithText(FOOD_POI_NAME)
            .performScrollTo()
            .performClick()

        composeRule.onNodeWithText(NARRATION_CONTENT)
            .performScrollTo()
            .assertIsDisplayed()
        composeRule.onNodeWithText(
            getString(R.string.poi_detail_narration_source, NARRATION_SOURCE),
        ).performScrollTo().assertIsDisplayed()
        composeRule.onNodeWithText(getString(R.string.poi_detail_navigate))
            .performScrollTo()
            .performClick()

        assertEquals(FOOD_POI_ID, openedNavigationTarget.get()?.poiId)
        assertEquals(FOOD_POI_NAME, openedNavigationTarget.get()?.displayName)
    }

    @Test
    fun activePackageFoodSearchStillWorksAfterConnectivityBecomesOffline() {
        setDemoContent()

        composeRule.runOnIdle {
            connectivity.value = ConnectivityUiState.Offline
        }
        composeRule.onNodeWithText(getString(R.string.connectivity_offline))
            .assertIsDisplayed()

        submitFoodQuery(FOOD_QUERY_UNACCENTED)
        composeRule.onNodeWithText(FOOD_POI_NAME)
            .performScrollTo()
            .assertIsDisplayed()
        assertEquals(ConnectivityUiState.Offline, connectivity.value)
        assertEquals(FOOD_QUERY_UNACCENTED, homeViewModel.uiState.value.nearbyQuery)
    }

    private fun setDemoContent() {
        composeRule.setContent {
            val homeUiState by homeViewModel.uiState.collectAsStateWithLifecycle()
            val connectivityState by connectivity.collectAsStateWithLifecycle()
            TravelAssistantAppContent(
                homeUiState = homeUiState,
                appShellUiState = AppShellUiState(
                    connectivity = connectivityState,
                    localPackage = LocalPackageUiState.Available(
                        version = "fixture-1",
                        publishedAtEpochMillis = FIXTURE_TIMESTAMP,
                    ),
                ),
                onUseCurrentLocation = homeViewModel::onLocationPermissionGranted,
                onOpenLocationSettings = {},
                onNearbyQueryChanged = homeViewModel::onNearbyQueryChanged,
                poiDetailContent = { poiId, onBack ->
                    RoomBackedPoiDetail(
                        poiId = poiId,
                        repository = detailRepository,
                        onBack = onBack,
                        onNavigate = openedNavigationTarget::set,
                    )
                },
            )
        }
        composeRule.runOnIdle(homeViewModel::onLocationPermissionGranted)
        composeRule.waitUntil(timeoutMillis = STATE_TIMEOUT_MILLIS) {
            homeViewModel.uiState.value.nearbySearchState is NearbySearchUiState.Content
        }
    }

    private fun submitFoodQuery(query: String) {
        composeRule.onNodeWithText(getString(R.string.nearby_search_label))
            .performTextInput(query)
        composeRule.waitUntil(timeoutMillis = STATE_TIMEOUT_MILLIS) {
            homeViewModel.uiState.value.nearbyQuery == query
        }
        composeRule.waitUntil(timeoutMillis = STATE_TIMEOUT_MILLIS) {
            homeViewModel.uiState.value.nearbySearchState !is NearbySearchUiState.Loading
        }
        val content = homeViewModel.uiState.value.nearbySearchState
            as NearbySearchUiState.Content
        assertEquals(FOOD_POI_ID, content.results.first().poiId)
        assertTrue(content.results.any { it.poiId == FOOD_POI_ID })
    }

    private fun getString(resourceId: Int, vararg formatArgs: Any): String =
        ApplicationProvider.getApplicationContext<android.content.Context>()
            .getString(resourceId, *formatArgs)

    private class FixedAppInfoRepository : AppInfoRepository {
        private val mutableAppName = MutableStateFlow("Travel Assistant")
        override val appName: StateFlow<String> = mutableAppName.asStateFlow()
    }

    private class FixedHcmcLocationClient : LocationClient {
        override suspend fun getCurrentLocation(): LocationAcquisitionResult =
            LocationAcquisitionResult.Success(
                DeviceLocation(
                    latitude = HCMC_LATITUDE,
                    longitude = HCMC_LONGITUDE,
                    accuracyMeters = 5f,
                    capturedAtEpochMillis = FIXTURE_TIMESTAMP,
                ),
            )
    }

    private companion object {
        const val FOOD_POI_ID = "hcmc-poi-ben-thanh-market"
        const val FOOD_POI_NAME = "Chợ Bến Thành"
        const val FOOD_MENU_ITEM_ID = "t091-menu-pho"
        const val FOOD_NARRATION_ID = "t091-narration-ben-thanh"
        const val FOOD_DISH = "Phở bò"
        const val FOOD_QUERY_ACCENTED = "phở bò"
        const val FOOD_QUERY_UNACCENTED = "pho bo"
        const val NARRATION_CONTENT = "Nội dung thuyết minh HCMC đã xác minh."
        const val NARRATION_SOURCE = "Ban quản lý điểm đến"
        const val FIXTURE_TIMESTAMP = 1_767_225_600_000L
        const val HCMC_LATITUDE = 10.7725
        const val HCMC_LONGITUDE = 106.6980
        const val STATE_TIMEOUT_MILLIS = 5_000L
    }
}

@Composable
private fun RoomBackedPoiDetail(
    poiId: String,
    repository: RoomPoiDetailRepository,
    onBack: () -> Unit,
    onNavigate: (PoiNavigationTarget) -> Unit,
) {
    val viewModel = remember(poiId, repository) {
        PoiDetailViewModel(
            savedStateHandle = SavedStateHandle(
                mapOf(PoiDetailDestination.POI_ID_ARGUMENT to poiId),
            ),
            repository = repository,
        )
    }
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()
    PoiDetailScreen(
        uiState = uiState,
        onBack = onBack,
        onRetry = viewModel::retry,
        onNavigate = onNavigate,
    )
}
