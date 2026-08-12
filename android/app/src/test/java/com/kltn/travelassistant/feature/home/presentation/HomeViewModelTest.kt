package com.kltn.travelassistant.feature.home.presentation

import com.kltn.travelassistant.analytics.GeocontextResultState
import com.kltn.travelassistant.analytics.ProductAnalytics
import com.kltn.travelassistant.analytics.ProductAnalyticsEvent
import com.kltn.travelassistant.data.location.DeviceLocation
import com.kltn.travelassistant.data.location.LocationAcquisitionResult
import com.kltn.travelassistant.data.location.LocationClient
import com.kltn.travelassistant.data.repository.AppInfoRepository
import com.kltn.travelassistant.feature.home.domain.DemoLocationPreset
import com.kltn.travelassistant.feature.home.domain.DemoLocationPresetProvider
import com.kltn.travelassistant.feature.nearby.domain.NearbyPoi
import com.kltn.travelassistant.feature.nearby.domain.NearbySearchRepository
import com.kltn.travelassistant.feature.nearby.domain.NearbySearchResult
import com.kltn.travelassistant.feature.nearby.domain.PoiCategoryLabel
import java.util.ArrayDeque
import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.NonCancellable
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.advanceUntilIdle
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.runCurrent
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.test.setMain
import kotlinx.coroutines.withContext
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test

@OptIn(ExperimentalCoroutinesApi::class)
class HomeViewModelTest {
    private val dispatcher = StandardTestDispatcher()

    @Before
    fun setUp() {
        Dispatchers.setMain(dispatcher)
    }

    @After
    fun tearDown() {
        Dispatchers.resetMain()
    }

    @Test
    fun initialUiStateDoesNotRequestLocation() = runTest(dispatcher) {
        val locationClient = FakeLocationClient(successResult)
        val viewModel = createViewModel(locationClient = locationClient)

        assertEquals(
            HomeUiState(appName = "Initial name", locationState = LocationUiState.Idle),
            viewModel.uiState.value,
        )
        assertEquals(0, locationClient.requestCount)
        assertEquals(
            NearbySearchUiState.WaitingForLocation,
            viewModel.uiState.value.nearbySearchState,
        )
    }

    @Test
    fun debugPresetsAreInitiallyUnselectedAndRealGpsRemainsTheDefaultAction() =
        runTest(dispatcher) {
            val locationClient = FakeLocationClient(successResult)
            val viewModel = createViewModel(
                locationClient = locationClient,
                demoLocationPresetProvider = demoPresetProvider(),
            )

            assertEquals(null, viewModel.uiState.value.selectedDemoLocationPresetId)
            assertEquals(
                listOf("hcmc", "bangkok"),
                viewModel.uiState.value.demoLocationPresets.map(DemoLocationPresetUiModel::id),
            )
            assertEquals(LocationUiState.Idle, viewModel.uiState.value.locationState)
            assertEquals(0, locationClient.requestCount)

            viewModel.onLocationPermissionGranted()
            advanceUntilIdle()

            assertEquals(LocationUiState.Available(testLocation), viewModel.uiState.value.locationState)
            assertEquals(null, viewModel.uiState.value.selectedDemoLocationPresetId)
            assertEquals(1, locationClient.requestCount)
        }

    @Test
    fun hcmcPresetAppliesTransientLocationPreservesQueryAndSkipsLocationClient() =
        runTest(dispatcher) {
            val locationClient = FakeLocationClient(LocationAcquisitionResult.PermissionDenied)
            val repository = FakeNearbySearchRepository()
            val viewModel = createViewModel(
                locationClient = locationClient,
                nearbySearchRepository = repository,
                demoLocationPresetProvider = demoPresetProvider(),
            )
            viewModel.onNearbyQueryChanged("museum")

            viewModel.onDemoLocationPresetSelected("hcmc")
            advanceUntilIdle()

            assertEquals("museum", viewModel.uiState.value.nearbyQuery)
            assertEquals("hcmc", viewModel.uiState.value.selectedDemoLocationPresetId)
            assertEquals(
                LocationUiState.Available(hcmcDemoLocation),
                viewModel.uiState.value.locationState,
            )
            assertEquals(0, locationClient.requestCount)
            assertEquals(
                listOf(SearchRequest(10.7799, 106.7, "museum")),
                repository.requests,
            )
        }

    @Test
    fun bangkokPresetAppliesWatPhoReferenceWithoutPermissionOrLocationClient() =
        runTest(dispatcher) {
            val locationClient = FakeLocationClient(LocationAcquisitionResult.PermissionDenied)
            val repository = FakeNearbySearchRepository()
            val viewModel = createViewModel(
                locationClient = locationClient,
                nearbySearchRepository = repository,
                demoLocationPresetProvider = demoPresetProvider(),
            )

            viewModel.onDemoLocationPresetSelected("bangkok")
            advanceUntilIdle()

            assertEquals("bangkok", viewModel.uiState.value.selectedDemoLocationPresetId)
            assertEquals(
                LocationUiState.Available(bangkokDemoLocation),
                viewModel.uiState.value.locationState,
            )
            assertEquals(0, locationClient.requestCount)
            assertEquals(
                listOf(SearchRequest(13.746508, 100.493096, "")),
                repository.requests,
            )
        }

    @Test
    fun presetCancelsRealAcquisitionAndStaleRealResultCannotOverwriteIt() =
        runTest(dispatcher) {
            val staleRealResult = CompletableDeferred<LocationAcquisitionResult>()
            val locationClient = NonCooperativeLocationClient(staleRealResult)
            val viewModel = createViewModel(
                locationClient = locationClient,
                demoLocationPresetProvider = demoPresetProvider(),
            )
            viewModel.onLocationPermissionGranted()
            runCurrent()

            viewModel.onDemoLocationPresetSelected("hcmc")
            runCurrent()
            staleRealResult.complete(successResult)
            advanceUntilIdle()

            assertEquals("hcmc", viewModel.uiState.value.selectedDemoLocationPresetId)
            assertEquals(
                LocationUiState.Available(hcmcDemoLocation),
                viewModel.uiState.value.locationState,
            )
            assertEquals(1, locationClient.requestCount)
        }

    @Test
    fun stalePermissionCallbackCannotReplaceANewerPreset() = runTest(dispatcher) {
        val locationClient = FakeLocationClient(successResult)
        val viewModel = createViewModel(
            locationClient = locationClient,
            demoLocationPresetProvider = demoPresetProvider(),
        )
        val staleActionId = requireNotNull(viewModel.onLocationPermissionRequestStarted())

        viewModel.onDemoLocationPresetSelected("bangkok")
        viewModel.onLocationPermissionGranted(staleActionId)
        advanceUntilIdle()

        assertEquals("bangkok", viewModel.uiState.value.selectedDemoLocationPresetId)
        assertEquals(LocationUiState.Available(bangkokDemoLocation), viewModel.uiState.value.locationState)
        assertEquals(0, locationClient.requestCount)
    }

    @Test
    fun explicitRealGpsActionReplacesSelectedPreset() = runTest(dispatcher) {
        val realLocation = testLocation.copy(latitude = 10.7725, longitude = 106.698)
        val locationClient = FakeLocationClient(LocationAcquisitionResult.Success(realLocation))
        val viewModel = createViewModel(
            locationClient = locationClient,
            demoLocationPresetProvider = demoPresetProvider(),
        )
        viewModel.onDemoLocationPresetSelected("bangkok")
        advanceUntilIdle()

        viewModel.onLocationPermissionGranted()
        advanceUntilIdle()

        assertEquals(null, viewModel.uiState.value.selectedDemoLocationPresetId)
        assertEquals(LocationUiState.Available(realLocation), viewModel.uiState.value.locationState)
        assertEquals(1, locationClient.requestCount)
    }

    @Test
    fun switchingHcmcToBangkokUsesLatestPresetAndRejectsStaleSearch() =
        runTest(dispatcher) {
            val hcmcResult = CompletableDeferred<NearbySearchResult>()
            val bangkokResult = CompletableDeferred<NearbySearchResult>()
            val repository = CoordinateDeferredSearchRepository(
                firstResult = hcmcResult,
                secondResult = bangkokResult,
            )
            val viewModel = createViewModel(
                nearbySearchRepository = repository,
                demoLocationPresetProvider = demoPresetProvider(),
            )
            viewModel.onDemoLocationPresetSelected("hcmc")
            runCurrent()
            viewModel.onDemoLocationPresetSelected("bangkok")
            runCurrent()
            bangkokResult.complete(NearbySearchResult.Success(listOf(defaultNearbyPois.last())))
            runCurrent()
            hcmcResult.complete(NearbySearchResult.Success(listOf(defaultNearbyPois.first())))
            advanceUntilIdle()

            assertEquals("bangkok", viewModel.uiState.value.selectedDemoLocationPresetId)
            assertEquals(
                NearbySearchUiState.Content(listOf(defaultNearbyPois.last())),
                viewModel.uiState.value.nearbySearchState,
            )
            assertEquals(
                listOf(10.7799, 13.746508),
                repository.requests.map(SearchRequest::latitude),
            )
        }

    @Test
    fun switchingBangkokToHcmcUsesLatestPreset() = runTest(dispatcher) {
        val repository = FakeNearbySearchRepository()
        val viewModel = createViewModel(
            nearbySearchRepository = repository,
            demoLocationPresetProvider = demoPresetProvider(),
        )

        viewModel.onDemoLocationPresetSelected("bangkok")
        advanceUntilIdle()
        viewModel.onDemoLocationPresetSelected("hcmc")
        advanceUntilIdle()

        assertEquals("hcmc", viewModel.uiState.value.selectedDemoLocationPresetId)
        assertEquals(LocationUiState.Available(hcmcDemoLocation), viewModel.uiState.value.locationState)
        assertEquals(
            listOf(13.746508, 10.7799),
            repository.requests.map(SearchRequest::latitude),
        )
    }

    @Test
    fun queryChangesUseCurrentlySelectedPresetLocation() = runTest(dispatcher) {
        val repository = FakeNearbySearchRepository()
        val viewModel = createViewModel(
            nearbySearchRepository = repository,
            demoLocationPresetProvider = demoPresetProvider(),
        )
        viewModel.onDemoLocationPresetSelected("bangkok")
        advanceUntilIdle()

        viewModel.onNearbyQueryChanged("temple")
        advanceUntilIdle()

        assertEquals(
            SearchRequest(13.746508, 100.493096, "temple"),
            repository.requests.last(),
        )
    }

    @Test
    fun stalePresetSearchCannotOverwriteNewerRealGpsSearch() = runTest(dispatcher) {
        val presetResult = CompletableDeferred<NearbySearchResult>()
        val realResult = CompletableDeferred<NearbySearchResult>()
        val repository = CoordinateDeferredSearchRepository(presetResult, realResult)
        val realLocation = testLocation.copy(latitude = 10.7725, longitude = 106.698)
        val viewModel = createViewModel(
            locationClient = FakeLocationClient(LocationAcquisitionResult.Success(realLocation)),
            nearbySearchRepository = repository,
            demoLocationPresetProvider = demoPresetProvider(),
        )
        viewModel.onDemoLocationPresetSelected("hcmc")
        runCurrent()
        viewModel.onLocationPermissionGranted()
        runCurrent()
        realResult.complete(NearbySearchResult.Success(listOf(defaultNearbyPois.last())))
        runCurrent()
        presetResult.complete(NearbySearchResult.Success(listOf(defaultNearbyPois.first())))
        advanceUntilIdle()

        assertEquals(null, viewModel.uiState.value.selectedDemoLocationPresetId)
        assertEquals(LocationUiState.Available(realLocation), viewModel.uiState.value.locationState)
        assertEquals(
            NearbySearchUiState.Content(listOf(defaultNearbyPois.last())),
            viewModel.uiState.value.nearbySearchState,
        )
    }

    @Test
    fun presetSearchDoesNotEmitProductionGeocontextAnalytics() = runTest(dispatcher) {
        val analytics = RecordingProductAnalytics()
        val viewModel = createViewModel(
            demoLocationPresetProvider = demoPresetProvider(),
            productAnalytics = analytics,
        )

        viewModel.onDemoLocationPresetSelected("hcmc")
        advanceUntilIdle()
        viewModel.onNearbyQueryChanged("market")
        advanceUntilIdle()
        viewModel.onDemoLocationPresetSelected("bangkok")
        advanceUntilIdle()

        assertTrue(analytics.events.isEmpty())
    }

    @Test
    fun aNewViewModelDoesNotRestorePreviouslySelectedPreset() = runTest(dispatcher) {
        val provider = demoPresetProvider()
        val first = createViewModel(demoLocationPresetProvider = provider)
        first.onDemoLocationPresetSelected("hcmc")
        advanceUntilIdle()
        assertEquals("hcmc", first.uiState.value.selectedDemoLocationPresetId)

        val recreated = createViewModel(demoLocationPresetProvider = provider)

        assertEquals(null, recreated.uiState.value.selectedDemoLocationPresetId)
        assertEquals(LocationUiState.Idle, recreated.uiState.value.locationState)
        assertEquals(NearbySearchUiState.WaitingForLocation, recreated.uiState.value.nearbySearchState)
    }

    @Test
    fun explicitPermissionRequestEntersLoadingWithoutRetrievingLocation() = runTest(dispatcher) {
        val locationClient = FakeLocationClient(successResult)
        val viewModel = createViewModel(locationClient = locationClient)

        viewModel.onLocationPermissionRequestStarted()

        assertEquals(LocationUiState.Loading, viewModel.uiState.value.locationState)
        assertEquals(0, locationClient.requestCount)
    }

    @Test
    fun grantedPermissionAndFakeSuccessReachAvailable() = runTest(dispatcher) {
        val locationClient = FakeLocationClient(successResult)
        val nearbyRepository = FakeNearbySearchRepository()
        val viewModel = createViewModel(
            locationClient = locationClient,
            nearbySearchRepository = nearbyRepository,
        )

        viewModel.onLocationPermissionGranted()
        assertEquals(LocationUiState.Loading, viewModel.uiState.value.locationState)
        advanceUntilIdle()

        assertEquals(LocationUiState.Available(testLocation), viewModel.uiState.value.locationState)
        assertEquals(1, locationClient.requestCount)
        assertEquals(listOf(SearchRequest(testLocation.latitude, testLocation.longitude, "")), nearbyRepository.requests)
        assertEquals(
            NearbySearchUiState.Content(defaultNearbyPois),
            viewModel.uiState.value.nearbySearchState,
        )
    }

    @Test
    fun firstSuccessfulLocationBackedSearchEmitsOneGeocontextOpenPerViewModel() =
        runTest(dispatcher) {
            val analytics = RecordingProductAnalytics()
            val viewModel = createViewModel(productAnalytics = analytics)

            viewModel.onLocationPermissionGranted()
            advanceUntilIdle()
            viewModel.onNearbyQueryChanged("ben thanh")
            advanceUntilIdle()
            viewModel.onLocationPermissionGranted()
            advanceUntilIdle()

            assertEquals(
                listOf(
                    ProductAnalyticsEvent.GeocontextOpened(
                        GeocontextResultState.CONTENT,
                    ),
                ),
                analytics.events,
            )
        }

    @Test
    fun emptyGeocontextIsTypedAndFailuresOrCancellationEmitNothing() = runTest(dispatcher) {
        val analytics = RecordingProductAnalytics()
        val failing = createViewModel(
            locationClient = FakeLocationClient(LocationAcquisitionResult.Failure),
            productAnalytics = analytics,
        )
        failing.onLocationPermissionGranted()
        advanceUntilIdle()
        assertTrue(analytics.events.isEmpty())

        val empty = createViewModel(
            nearbySearchRepository = FakeNearbySearchRepository {
                NearbySearchResult.Success(emptyList())
            },
            productAnalytics = analytics,
        )
        empty.onLocationPermissionGranted()
        advanceUntilIdle()

        assertEquals(
            listOf(ProductAnalyticsEvent.GeocontextOpened(GeocontextResultState.EMPTY)),
            analytics.events,
        )
    }

    @Test
    fun backgroundedPendingNearbyResultCannotEmitGeocontextOpen() = runTest(dispatcher) {
        val analytics = RecordingProductAnalytics()
        val pending = CompletableDeferred<NearbySearchResult>()
        val repository = object : NearbySearchRepository {
            override suspend fun search(
                latitude: Double,
                longitude: Double,
                query: String,
            ): NearbySearchResult = withContext(NonCancellable) { pending.await() }
        }
        val viewModel = createViewModel(
            nearbySearchRepository = repository,
            productAnalytics = analytics,
        )

        viewModel.onLocationPermissionGranted()
        runCurrent()
        viewModel.onLocationRequestCancelled()
        pending.complete(NearbySearchResult.Success(defaultNearbyPois))
        advanceUntilIdle()

        assertTrue(analytics.events.isEmpty())
    }

    @Test
    fun deniedPermissionReachesRecoverablePermissionDenied() = runTest(dispatcher) {
        val locationClient = FakeLocationClient(successResult)
        val viewModel = createViewModel(locationClient = locationClient)

        viewModel.onLocationPermissionRequestStarted()
        viewModel.onLocationPermissionDenied(canRequestPermissionAgain = false)

        assertEquals(
            LocationUiState.PermissionDenied(canRequestPermissionAgain = false),
            viewModel.uiState.value.locationState,
        )
        assertEquals(0, locationClient.requestCount)
    }

    @Test
    fun providerFailureAndTimeoutReachDistinctErrorStates() = runTest(dispatcher) {
        val locationClient = FakeLocationClient(
            LocationAcquisitionResult.ProviderUnavailable,
            LocationAcquisitionResult.Timeout,
        )
        val viewModel = createViewModel(locationClient = locationClient)

        viewModel.onLocationPermissionGranted()
        advanceUntilIdle()
        assertEquals(
            LocationUiState.Error(LocationError.PROVIDER_UNAVAILABLE),
            viewModel.uiState.value.locationState,
        )

        viewModel.onLocationPermissionGranted()
        advanceUntilIdle()
        assertEquals(
            LocationUiState.Error(LocationError.TIMEOUT),
            viewModel.uiState.value.locationState,
        )
    }

    @Test
    fun retryRecoversFromPermissionDenied() = runTest(dispatcher) {
        val locationClient = FakeLocationClient(successResult)
        val viewModel = createViewModel(locationClient = locationClient)

        viewModel.onLocationPermissionDenied(canRequestPermissionAgain = true)
        viewModel.onLocationPermissionGranted()
        advanceUntilIdle()

        assertEquals(LocationUiState.Available(testLocation), viewModel.uiState.value.locationState)
        assertEquals(1, locationClient.requestCount)
    }

    @Test
    fun retryRecoversFromError() = runTest(dispatcher) {
        val locationClient = FakeLocationClient(
            LocationAcquisitionResult.Failure,
            successResult,
        )
        val viewModel = createViewModel(locationClient = locationClient)

        viewModel.onLocationPermissionGranted()
        advanceUntilIdle()
        assertEquals(
            LocationUiState.Error(LocationError.FAILED),
            viewModel.uiState.value.locationState,
        )

        viewModel.onLocationPermissionGranted()
        advanceUntilIdle()
        assertEquals(LocationUiState.Available(testLocation), viewModel.uiState.value.locationState)
        assertEquals(2, locationClient.requestCount)
    }

    @Test
    fun duplicateAcquisitionRequestIsIgnoredWhileLoading() = runTest(dispatcher) {
        val pendingResult = CompletableDeferred<LocationAcquisitionResult>()
        val locationClient = SuspendedLocationClient(pendingResult)
        val viewModel = createViewModel(locationClient = locationClient)

        viewModel.onLocationPermissionGranted()
        runCurrent()
        viewModel.onLocationPermissionGranted()
        runCurrent()

        assertEquals(LocationUiState.Loading, viewModel.uiState.value.locationState)
        assertEquals(1, locationClient.requestCount)

        pendingResult.complete(successResult)
        advanceUntilIdle()
        assertEquals(LocationUiState.Available(testLocation), viewModel.uiState.value.locationState)
    }

    @Test
    fun activeAcquisitionCanBeCancelledWhenAppLeavesForeground() = runTest(dispatcher) {
        val pendingResult = CompletableDeferred<LocationAcquisitionResult>()
        val locationClient = SuspendedLocationClient(pendingResult)
        val viewModel = createViewModel(locationClient = locationClient)

        viewModel.onLocationPermissionGranted()
        runCurrent()
        viewModel.onLocationRequestCancelled()
        runCurrent()

        assertEquals(
            LocationUiState.Error(LocationError.CANCELLED),
            viewModel.uiState.value.locationState,
        )
        assertEquals(1, locationClient.requestCount)
    }

    @Test
    fun repositoryStateChangesReachUiState() = runTest(dispatcher) {
        val repository = FakeAppInfoRepository("Initial name")
        val viewModel = HomeViewModel(
            repository,
            FakeLocationClient(successResult),
            FakeNearbySearchRepository(),
            FakeDemoLocationPresetProvider(),
        )

        repository.updateAppName("Updated name")
        advanceUntilIdle()

        assertEquals("Updated name", viewModel.uiState.value.appName)
        assertEquals(LocationUiState.Idle, viewModel.uiState.value.locationState)
    }

    @Test
    fun exposedUiStateIsNotMutableStateFlow() = runTest(dispatcher) {
        val viewModel = createViewModel()

        assertFalse(viewModel.uiState is MutableStateFlow<*>)
    }

    @Test
    fun queryUpdateFiltersAndClearingRestoresNearbyResults() = runTest(dispatcher) {
        val repository = FakeNearbySearchRepository { request ->
            NearbySearchResult.Success(
                if (request.query.isBlank()) defaultNearbyPois else listOf(defaultNearbyPois.last()),
            )
        }
        val viewModel = createViewModel(nearbySearchRepository = repository)
        viewModel.onLocationPermissionGranted()
        advanceUntilIdle()

        viewModel.onNearbyQueryChanged("ben thanh")
        advanceUntilIdle()
        assertEquals("ben thanh", viewModel.uiState.value.nearbyQuery)
        assertEquals(
            NearbySearchUiState.Content(listOf(defaultNearbyPois.last())),
            viewModel.uiState.value.nearbySearchState,
        )

        viewModel.onNearbyQueryChanged("")
        advanceUntilIdle()
        assertEquals(NearbySearchUiState.Content(defaultNearbyPois), viewModel.uiState.value.nearbySearchState)
        assertEquals(listOf("", "ben thanh", ""), repository.requests.map(SearchRequest::query))
    }

    @Test
    fun duplicateQueryDoesNotStartAnotherSearch() = runTest(dispatcher) {
        val repository = FakeNearbySearchRepository()
        val viewModel = createViewModel(nearbySearchRepository = repository)
        viewModel.onLocationPermissionGranted()
        advanceUntilIdle()

        viewModel.onNearbyQueryChanged("museum")
        viewModel.onNearbyQueryChanged("museum")
        advanceUntilIdle()

        assertEquals(listOf("", "museum"), repository.requests.map(SearchRequest::query))
    }

    @Test
    fun cancelledStaleSearchCannotReplaceTheLatestResults() = runTest(dispatcher) {
        val staleResult = CompletableDeferred<NearbySearchResult>()
        val latestResult = CompletableDeferred<NearbySearchResult>()
        val repository = StaleResultNearbySearchRepository(staleResult, latestResult)
        val viewModel = createViewModel(nearbySearchRepository = repository)
        viewModel.onLocationPermissionGranted()
        advanceUntilIdle()

        viewModel.onNearbyQueryChanged("old")
        runCurrent()
        viewModel.onNearbyQueryChanged("new")
        runCurrent()
        latestResult.complete(NearbySearchResult.Success(listOf(defaultNearbyPois.last())))
        runCurrent()

        assertEquals(
            NearbySearchUiState.Content(listOf(defaultNearbyPois.last())),
            viewModel.uiState.value.nearbySearchState,
        )

        staleResult.complete(NearbySearchResult.Success(listOf(defaultNearbyPois.first())))
        advanceUntilIdle()
        assertEquals(
            NearbySearchUiState.Content(listOf(defaultNearbyPois.last())),
            viewModel.uiState.value.nearbySearchState,
        )
    }

    @Test
    fun refreshedLocationRecomputesNearbyOrderingAndDistance() = runTest(dispatcher) {
        val refreshedLocation = testLocation.copy(latitude = 10.7000)
        val repository = FakeNearbySearchRepository { request ->
            val results = if (request.latitude == testLocation.latitude) {
                defaultNearbyPois
            } else {
                defaultNearbyPois.reversed().mapIndexed { index, poi ->
                    poi.copy(distanceMeters = 100.0 + index)
                }
            }
            NearbySearchResult.Success(results)
        }
        val viewModel = createViewModel(
            locationClient = FakeLocationClient(
                successResult,
                LocationAcquisitionResult.Success(refreshedLocation),
            ),
            nearbySearchRepository = repository,
        )

        viewModel.onLocationPermissionGranted()
        advanceUntilIdle()
        viewModel.onLocationPermissionGranted()
        advanceUntilIdle()

        val content = viewModel.uiState.value.nearbySearchState as NearbySearchUiState.Content
        assertEquals(defaultNearbyPois.reversed().map(NearbyPoi::poiId), content.results.map(NearbyPoi::poiId))
        assertEquals(100.0, content.results.first().distanceMeters, 0.0)
        assertEquals(listOf(testLocation.latitude, refreshedLocation.latitude), repository.requests.map(SearchRequest::latitude))
    }

    @Test
    fun emptyAndDatabaseErrorStatesAreExplicitAndDoNotReplaceLocationState() = runTest(dispatcher) {
        val repository = FakeNearbySearchRepository { request ->
            if (request.query == "error") {
                NearbySearchResult.DatabaseError
            } else {
                NearbySearchResult.Success(emptyList())
            }
        }
        val viewModel = createViewModel(nearbySearchRepository = repository)

        viewModel.onLocationPermissionGranted()
        advanceUntilIdle()
        assertEquals(NearbySearchUiState.Empty, viewModel.uiState.value.nearbySearchState)
        assertEquals(LocationUiState.Available(testLocation), viewModel.uiState.value.locationState)

        viewModel.onNearbyQueryChanged("error")
        advanceUntilIdle()
        assertEquals(NearbySearchUiState.Error, viewModel.uiState.value.nearbySearchState)
        assertEquals(LocationUiState.Available(testLocation), viewModel.uiState.value.locationState)
    }

    private fun createViewModel(
        locationClient: LocationClient = FakeLocationClient(successResult),
        nearbySearchRepository: NearbySearchRepository = FakeNearbySearchRepository(),
        demoLocationPresetProvider: DemoLocationPresetProvider = FakeDemoLocationPresetProvider(),
        productAnalytics: ProductAnalytics = RecordingProductAnalytics(),
    ): HomeViewModel = HomeViewModel(
        repository = FakeAppInfoRepository("Initial name"),
        locationClient = locationClient,
        nearbySearchRepository = nearbySearchRepository,
        demoLocationPresetProvider = demoLocationPresetProvider,
        productAnalytics = productAnalytics,
    )

    private class FakeDemoLocationPresetProvider(
        override val presets: List<DemoLocationPreset> = emptyList(),
    ) : DemoLocationPresetProvider

    private class RecordingProductAnalytics : ProductAnalytics {
        val events = mutableListOf<ProductAnalyticsEvent>()

        override fun track(event: ProductAnalyticsEvent) {
            events += event
        }
    }

    private class FakeAppInfoRepository(initialAppName: String) : AppInfoRepository {
        private val mutableAppName = MutableStateFlow(initialAppName)

        override val appName: StateFlow<String> = mutableAppName.asStateFlow()

        fun updateAppName(appName: String) {
            mutableAppName.value = appName
        }
    }

    private class FakeLocationClient(
        vararg results: LocationAcquisitionResult,
    ) : LocationClient {
        private val results = ArrayDeque(results.toList())
        var requestCount: Int = 0
            private set

        override suspend fun getCurrentLocation(): LocationAcquisitionResult {
            requestCount += 1
            return results.removeFirst()
        }
    }

    private class SuspendedLocationClient(
        private val result: CompletableDeferred<LocationAcquisitionResult>,
    ) : LocationClient {
        var requestCount: Int = 0
            private set

        override suspend fun getCurrentLocation(): LocationAcquisitionResult {
            requestCount += 1
            return result.await()
        }
    }

    private class NonCooperativeLocationClient(
        private val result: CompletableDeferred<LocationAcquisitionResult>,
    ) : LocationClient {
        var requestCount: Int = 0
            private set

        override suspend fun getCurrentLocation(): LocationAcquisitionResult {
            requestCount += 1
            return withContext(NonCancellable) { result.await() }
        }
    }

    private class CoordinateDeferredSearchRepository(
        private val firstResult: CompletableDeferred<NearbySearchResult>,
        private val secondResult: CompletableDeferred<NearbySearchResult>,
    ) : NearbySearchRepository {
        val requests = mutableListOf<SearchRequest>()

        override suspend fun search(
            latitude: Double,
            longitude: Double,
            query: String,
        ): NearbySearchResult {
            requests += SearchRequest(latitude, longitude, query)
            return when (requests.size) {
                1 -> withContext(NonCancellable) { firstResult.await() }
                2 -> secondResult.await()
                else -> error("Unexpected search request")
            }
        }
    }

    private class StaleResultNearbySearchRepository(
        private val staleResult: CompletableDeferred<NearbySearchResult>,
        private val latestResult: CompletableDeferred<NearbySearchResult>,
    ) : NearbySearchRepository {
        override suspend fun search(
            latitude: Double,
            longitude: Double,
            query: String,
        ): NearbySearchResult = when (query) {
            "" -> NearbySearchResult.Success(defaultNearbyPois)
            "old" -> withContext(NonCancellable) { staleResult.await() }
            "new" -> latestResult.await()
            else -> error("Unexpected query")
        }
    }

    private class FakeNearbySearchRepository(
        private val resultProvider: (SearchRequest) -> NearbySearchResult = {
            NearbySearchResult.Success(defaultNearbyPois)
        },
    ) : NearbySearchRepository {
        val requests = mutableListOf<SearchRequest>()

        override suspend fun search(
            latitude: Double,
            longitude: Double,
            query: String,
        ): NearbySearchResult {
            val request = SearchRequest(latitude, longitude, query)
            requests += request
            return resultProvider(request)
        }
    }

    private data class SearchRequest(
        val latitude: Double,
        val longitude: Double,
        val query: String,
    )

    private companion object {
        val testLocation = DeviceLocation(
            latitude = 10.7799,
            longitude = 106.7,
            accuracyMeters = 12.5f,
            capturedAtEpochMillis = 1_753_200_000_000L,
        )
        val successResult = LocationAcquisitionResult.Success(testLocation)
        val hcmcDemoLocation = DeviceLocation(
            latitude = 10.7799,
            longitude = 106.7,
            accuracyMeters = null,
            capturedAtEpochMillis = null,
        )
        val bangkokDemoLocation = DeviceLocation(
            latitude = 13.746508,
            longitude = 100.493096,
            accuracyMeters = null,
            capturedAtEpochMillis = null,
        )
        val defaultNearbyPois = listOf(
            NearbyPoi(
                poiId = "post-office",
                displayName = "Bưu điện Trung tâm Sài Gòn",
                category = "landmark",
                categoryLabel = PoiCategoryLabel.LANDMARK,
                distanceMeters = 0.0,
            ),
            NearbyPoi(
                poiId = "ben-thanh",
                displayName = "Chợ Bến Thành",
                category = "market",
                categoryLabel = PoiCategoryLabel.MARKET,
                distanceMeters = 850.0,
            ),
        )

        fun demoPresetProvider(): DemoLocationPresetProvider = FakeDemoLocationPresetProvider(
            presets = listOf(
                DemoLocationPreset(
                    id = "hcmc",
                    label = "Demo: TP.HCM",
                    location = hcmcDemoLocation,
                ),
                DemoLocationPreset(
                    id = "bangkok",
                    label = "Demo: Bangkok",
                    location = bangkokDemoLocation,
                ),
            ),
        )
    }
}
