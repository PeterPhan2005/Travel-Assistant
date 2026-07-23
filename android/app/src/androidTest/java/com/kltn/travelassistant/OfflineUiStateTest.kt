package com.kltn.travelassistant

import androidx.compose.ui.test.assertCountEquals
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.assertIsEnabled
import androidx.compose.ui.test.hasScrollAction
import androidx.compose.ui.test.hasText
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onAllNodesWithContentDescription
import androidx.compose.ui.test.onAllNodesWithTag
import androidx.compose.ui.test.onAllNodesWithText
import androidx.compose.ui.test.onNodeWithContentDescription
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performScrollTo
import androidx.compose.ui.test.performScrollToNode
import androidx.room.Room
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.kltn.travelassistant.data.local.TravelAssistantDatabase
import com.kltn.travelassistant.data.location.DeviceLocation
import com.kltn.travelassistant.data.repository.RoomNearbySearchRepository
import com.kltn.travelassistant.data.seed.BundledHcmcSeedSource
import com.kltn.travelassistant.data.seed.RoomCuratedSeedImporter
import com.kltn.travelassistant.data.seed.SeedDocumentParser
import com.kltn.travelassistant.data.seed.SeedImportResult
import com.kltn.travelassistant.data.seed.SeedValidator
import com.kltn.travelassistant.feature.appshell.presentation.AppShellUiState
import com.kltn.travelassistant.feature.appshell.presentation.ConnectivityUiState
import com.kltn.travelassistant.feature.appshell.presentation.LOCAL_PACKAGE_METADATA_TEST_TAG
import com.kltn.travelassistant.feature.appshell.presentation.LocalPackageUiState
import com.kltn.travelassistant.feature.appshell.presentation.OFFLINE_WARNING_TEST_TAG
import com.kltn.travelassistant.feature.appshell.presentation.PackagePublicationDateFormatter
import com.kltn.travelassistant.feature.home.presentation.HomeUiState
import com.kltn.travelassistant.feature.home.presentation.LocationUiState
import com.kltn.travelassistant.feature.home.presentation.NearbySearchUiState
import com.kltn.travelassistant.feature.nearby.domain.NearbyPoi
import com.kltn.travelassistant.feature.nearby.domain.NearbySearchResult
import com.kltn.travelassistant.feature.nearby.domain.PoiCategoryLabel
import com.kltn.travelassistant.feature.poi.domain.PoiDetail
import com.kltn.travelassistant.feature.poi.domain.PoiNavigationTarget
import com.kltn.travelassistant.feature.poi.presentation.PoiDetailScreen
import com.kltn.travelassistant.feature.poi.presentation.PoiDetailUiState
import com.kltn.travelassistant.navigation.TopLevelDestination
import com.kltn.travelassistant.navigation.navigationItemTestTag
import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class OfflineUiStateTest {
    @get:Rule
    val composeRule = createComposeRule()

    @Test
    fun offlineWarningAndLocalSearchRemainVisibleWithoutGlobalPackageMetadata() {
        setAppContent(
            shellState = AppShellUiState(
                connectivity = ConnectivityUiState.Offline,
                localPackage = availablePackage,
            ),
        )

        composeRule.onNodeWithText(getString(R.string.connectivity_offline)).assertIsDisplayed()
        composeRule.onNodeWithContentDescription(
            getString(R.string.connectivity_offline_dismiss),
        ).assertIsDisplayed()
        composeRule.onAllNodesWithTag(LOCAL_PACKAGE_METADATA_TEST_TAG).assertCountEquals(0)
        assertAvailablePackageMetadataDoesNotExist()
        composeRule.onNodeWithText(nearbyPoi.displayName)
            .performScrollTo()
            .assertIsDisplayed()
        composeRule.onNodeWithText(getString(R.string.nearby_search_label))
            .assertIsDisplayed()
            .assertIsEnabled()
    }

    @Test
    fun offlineWarningCloseActionInvokesDismissal() {
        var dismissalRequested = false
        setAppContent(
            shellState = AppShellUiState(
                connectivity = ConnectivityUiState.Offline,
                localPackage = availablePackage,
            ),
            onDismissOfflineWarning = { dismissalRequested = true },
        )

        composeRule.onNodeWithContentDescription(
            getString(R.string.connectivity_offline_dismiss),
        ).assertIsDisplayed().performClick()

        assertTrue(dismissalRequested)
    }

    @Test
    fun dismissedOfflineWarningKeepsLocalContentVisibleWithoutPackageMetadata() {
        setAppContent(
            shellState = AppShellUiState(
                connectivity = ConnectivityUiState.Offline,
                localPackage = availablePackage,
                isOfflineWarningDismissed = true,
            ),
        )

        composeRule.onAllNodesWithTag(OFFLINE_WARNING_TEST_TAG).assertCountEquals(0)
        composeRule.onAllNodesWithText(getString(R.string.connectivity_offline))
            .assertCountEquals(0)
        composeRule.onAllNodesWithContentDescription(
            getString(R.string.connectivity_offline_dismiss),
        ).assertCountEquals(0)
        composeRule.onAllNodesWithTag(LOCAL_PACKAGE_METADATA_TEST_TAG).assertCountEquals(0)
        assertAvailablePackageMetadataDoesNotExist()
        composeRule.onNodeWithText(nearbyPoi.displayName)
            .performScrollTo()
            .assertIsDisplayed()
        composeRule.onNodeWithText(getString(R.string.nearby_search_label))
            .assertIsDisplayed()
            .assertIsEnabled()
    }

    @Test
    fun packageMetadataIsVisibleOnlyInDownloadsAcrossTopLevelDestinations() {
        setAppContent(
            shellState = AppShellUiState(
                connectivity = ConnectivityUiState.Online,
                localPackage = availablePackage,
            ),
        )

        TopLevelDestination.all.forEach { destination ->
            composeRule.onNodeWithTag(navigationItemTestTag(destination)).assertIsDisplayed()
        }

        listOf(
            TopLevelDestination.EXPLORE,
            TopLevelDestination.ASSISTANT,
            TopLevelDestination.ITINERARY,
            TopLevelDestination.PROFILE,
        ).forEach { destination ->
            composeRule.onNodeWithTag(navigationItemTestTag(destination)).performClick()
            composeRule.onAllNodesWithTag(LOCAL_PACKAGE_METADATA_TEST_TAG).assertCountEquals(0)
            assertAvailablePackageMetadataDoesNotExist()
        }

        composeRule.onNodeWithTag(navigationItemTestTag(TopLevelDestination.DOWNLOADS))
            .performClick()
        composeRule.onNodeWithTag(LOCAL_PACKAGE_METADATA_TEST_TAG).assertIsDisplayed()
        composeRule.onNodeWithText(getString(R.string.local_package_title)).assertIsDisplayed()
        composeRule.onNodeWithText(
            getString(R.string.local_package_version, availablePackage.version),
        ).assertIsDisplayed()
        composeRule.onNodeWithText(
            getString(
                R.string.local_package_publication_date,
                availablePackagePublicationDate,
            ),
        ).assertIsDisplayed()
        composeRule.onAllNodesWithTag(OFFLINE_WARNING_TEST_TAG).assertCountEquals(0)
        composeRule.onAllNodesWithContentDescription(
            getString(R.string.connectivity_offline_dismiss),
        ).assertCountEquals(0)
    }

    @Test
    fun unavailablePackageMetadataShowsNeutralDownloadsMessageWithoutFabrication() {
        setAppContent(
            shellState = AppShellUiState(
                connectivity = ConnectivityUiState.Online,
                localPackage = LocalPackageUiState.Unavailable,
            ),
        )

        composeRule.onAllNodesWithTag(LOCAL_PACKAGE_METADATA_TEST_TAG).assertCountEquals(0)
        composeRule.onNodeWithTag(navigationItemTestTag(TopLevelDestination.DOWNLOADS))
            .performClick()

        composeRule.onNodeWithTag(LOCAL_PACKAGE_METADATA_TEST_TAG).assertIsDisplayed()
        composeRule.onNodeWithText(getString(R.string.local_package_unavailable))
            .assertIsDisplayed()
        composeRule.onAllNodesWithText("Phiên bản", substring = true).assertCountEquals(0)
        composeRule.onAllNodesWithText("Phát hành ngày", substring = true).assertCountEquals(0)
    }

    @Test
    fun invalidPackagePublicationDateShowsVersionAndOmitsDateInDownloads() {
        val invalidDatePackage = availablePackage.copy(publishedAtEpochMillis = 0)
        setAppContent(
            shellState = AppShellUiState(
                connectivity = ConnectivityUiState.Online,
                localPackage = invalidDatePackage,
            ),
        )

        composeRule.onNodeWithTag(navigationItemTestTag(TopLevelDestination.DOWNLOADS))
            .performClick()

        composeRule.onNodeWithText(
            getString(R.string.local_package_version, invalidDatePackage.version),
        ).assertIsDisplayed()
        composeRule.onAllNodesWithText("Phát hành ngày", substring = true).assertCountEquals(0)
    }

    @Test
    fun allBundledRoomResultsRemainDisplayedOffline() {
        runBlocking {
            val context = ApplicationProvider.getApplicationContext<android.content.Context>()
            val database = Room.inMemoryDatabaseBuilder(
                context,
                TravelAssistantDatabase::class.java,
            ).build()
            try {
                val parser = SeedDocumentParser()
                val importResult = RoomCuratedSeedImporter(
                    source = BundledHcmcSeedSource(context),
                    parser = parser,
                    validator = SeedValidator(parser),
                    database = database,
                ).importSeed()
                assertTrue(importResult is SeedImportResult.Imported)
                val searchResult = RoomNearbySearchRepository(database.poiContentDao()).search(
                    latitude = 10.7725,
                    longitude = 106.6980,
                    query = "",
                ) as NearbySearchResult.Success
                assertEquals(5, searchResult.pois.size)

                setAppContent(
                    shellState = AppShellUiState(
                        connectivity = ConnectivityUiState.Offline,
                        localPackage = availablePackage,
                    ),
                    homeUiState = homeState.copy(
                        nearbySearchState = NearbySearchUiState.Content(searchResult.pois),
                    ),
                )

                val lastPoiName = searchResult.pois.last().displayName
                composeRule.onNode(hasScrollAction())
                    .performScrollToNode(hasText(lastPoiName))
                composeRule.onNodeWithText(lastPoiName)
                    .assertIsDisplayed()
            } finally {
                database.close()
            }
        }
    }

    @Test
    fun onlineDoesNotShowFalseOfflineWarningOrGlobalPackageMetadata() {
        setAppContent(
            shellState = AppShellUiState(
                connectivity = ConnectivityUiState.Online,
                localPackage = LocalPackageUiState.Unavailable,
            ),
        )

        composeRule.onAllNodesWithText(getString(R.string.connectivity_offline))
            .assertCountEquals(0)
        composeRule.onAllNodesWithTag(OFFLINE_WARNING_TEST_TAG).assertCountEquals(0)
        composeRule.onAllNodesWithTag(LOCAL_PACKAGE_METADATA_TEST_TAG).assertCountEquals(0)
        composeRule.onAllNodesWithText(getString(R.string.local_package_unavailable))
            .assertCountEquals(0)
        composeRule.onAllNodesWithText("2026.07.1").assertCountEquals(0)
    }

    @Test
    fun checkingDoesNotShowOfflineOrBlockLocalContent() {
        setAppContent(
            shellState = AppShellUiState(
                connectivity = ConnectivityUiState.Checking,
                localPackage = LocalPackageUiState.Loading,
            ),
        )

        composeRule.onNodeWithText(getString(R.string.connectivity_checking)).assertIsDisplayed()
        composeRule.onAllNodesWithText(getString(R.string.connectivity_offline))
            .assertCountEquals(0)
        composeRule.onAllNodesWithTag(OFFLINE_WARNING_TEST_TAG).assertCountEquals(0)
        composeRule.onNodeWithText(nearbyPoi.displayName)
            .performScrollTo()
            .assertIsDisplayed()
        composeRule.onNodeWithText(getString(R.string.nearby_search_label)).assertIsEnabled()
    }

    @Test
    fun poiDetailBackAndExternalNavigationRemainAvailableOffline() {
        var navigationRequested = false
        setAppContent(
            shellState = AppShellUiState(
                connectivity = ConnectivityUiState.Offline,
                localPackage = availablePackage,
            ),
            poiDetailContent = { _, onBack ->
                PoiDetailScreen(
                    uiState = PoiDetailUiState.Content(poiDetail),
                    onBack = onBack,
                    onRetry = {},
                    onNavigate = { navigationRequested = true },
                )
            },
        )

        composeRule.onNodeWithText(nearbyPoi.displayName)
            .performScrollTo()
            .performClick()
        composeRule.onNodeWithText(poiDetail.name).assertIsDisplayed()
        composeRule.onAllNodesWithTag(LOCAL_PACKAGE_METADATA_TEST_TAG).assertCountEquals(0)
        assertAvailablePackageMetadataDoesNotExist()
        composeRule.onNodeWithText(getString(R.string.poi_detail_navigate))
            .assertIsDisplayed()
            .assertIsEnabled()
            .performClick()
        assertTrue(navigationRequested)

        composeRule.onNodeWithContentDescription(getString(R.string.poi_detail_back))
            .performClick()
        composeRule.onNodeWithText(nearbyPoi.displayName)
            .performScrollTo()
            .assertIsDisplayed()
    }

    @Test
    fun assistantAndDownloadsExplainInternetRequirementsWhileOffline() {
        setAppContent(
            shellState = AppShellUiState(
                connectivity = ConnectivityUiState.Offline,
                localPackage = availablePackage,
            ),
        )

        composeRule.onNodeWithTag(navigationItemTestTag(TopLevelDestination.ASSISTANT))
            .performClick()
        composeRule.onNodeWithText(getString(R.string.assistant_offline_explanation))
            .assertIsDisplayed()
        composeRule.onAllNodesWithTag(LOCAL_PACKAGE_METADATA_TEST_TAG).assertCountEquals(0)

        composeRule.onNodeWithTag(navigationItemTestTag(TopLevelDestination.DOWNLOADS))
            .performClick()
        composeRule.onNodeWithText(getString(R.string.downloads_offline_explanation))
            .assertIsDisplayed()
        composeRule.onNodeWithTag(LOCAL_PACKAGE_METADATA_TEST_TAG).assertIsDisplayed()
        composeRule.onNodeWithText(
            getString(R.string.local_package_version, availablePackage.version),
        ).assertIsDisplayed()
    }

    private fun setAppContent(
        shellState: AppShellUiState,
        homeUiState: HomeUiState = homeState,
        onDismissOfflineWarning: () -> Unit = {},
        poiDetailContent: @androidx.compose.runtime.Composable (
            poiId: String,
            onBack: () -> Unit,
        ) -> Unit = { _, _ -> },
    ) {
        composeRule.setContent {
            TravelAssistantAppContent(
                homeUiState = homeUiState,
                appShellUiState = shellState,
                onUseCurrentLocation = {},
                onOpenLocationSettings = {},
                onNearbyQueryChanged = {},
                onDismissOfflineWarning = onDismissOfflineWarning,
                poiDetailContent = poiDetailContent,
            )
        }
    }

    private fun getString(resourceId: Int, vararg formatArgs: Any): String =
        ApplicationProvider.getApplicationContext<android.content.Context>()
            .getString(resourceId, *formatArgs)

    private fun assertAvailablePackageMetadataDoesNotExist() {
        composeRule.onAllNodesWithText(getString(R.string.local_package_title))
            .assertCountEquals(0)
        composeRule.onAllNodesWithText(
            getString(R.string.local_package_version, availablePackage.version),
        ).assertCountEquals(0)
        composeRule.onAllNodesWithText(
            getString(
                R.string.local_package_publication_date,
                availablePackagePublicationDate,
            ),
        ).assertCountEquals(0)
    }

    private companion object {
        val nearbyPoi = NearbyPoi(
            poiId = "hcmc-poi-ben-thanh-market",
            displayName = "Chợ Bến Thành",
            category = "market",
            categoryLabel = PoiCategoryLabel.MARKET,
            distanceMeters = 25.0,
        )
        val homeState = HomeUiState(
            appName = "Travel Assistant",
            locationState = LocationUiState.Available(
                DeviceLocation(
                    latitude = 10.7725,
                    longitude = 106.6980,
                    accuracyMeters = 5f,
                    capturedAtEpochMillis = 1L,
                ),
            ),
            nearbySearchState = NearbySearchUiState.Content(listOf(nearbyPoi)),
        )
        val availablePackage = LocalPackageUiState.Available(
            version = "2026.07.1",
            publishedAtEpochMillis = 1_721_510_400_000L,
        )
        val availablePackagePublicationDate = PackagePublicationDateFormatter.format(
            availablePackage.publishedAtEpochMillis,
        )!!
        val poiDetail = PoiDetail(
            poiId = nearbyPoi.poiId,
            name = nearbyPoi.displayName,
            category = nearbyPoi.categoryLabel,
            city = "Ho Chi Minh City",
            area = null,
            address = null,
            shortDescription = "Dữ liệu chi tiết đã lưu trên thiết bị.",
            menuItems = emptyList(),
            narration = null,
            navigationTarget = PoiNavigationTarget(
                poiId = nearbyPoi.poiId,
                displayName = nearbyPoi.displayName,
                latitude = 10.7725,
                longitude = 106.6980,
            ),
        )
    }
}
