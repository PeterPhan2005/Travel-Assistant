package com.kltn.travelassistant.feature.home.presentation

import com.kltn.travelassistant.data.location.DeviceLocation
import com.kltn.travelassistant.data.location.LocationAcquisitionResult
import com.kltn.travelassistant.data.location.LocationClient
import com.kltn.travelassistant.data.repository.AppInfoRepository
import com.kltn.travelassistant.feature.nearby.domain.NearbyPoi
import com.kltn.travelassistant.feature.nearby.domain.NearbySearchRepository
import com.kltn.travelassistant.feature.nearby.domain.NearbySearchResult
import com.kltn.travelassistant.feature.nearby.domain.PoiCategoryLabel
import java.util.ArrayDeque
import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.advanceUntilIdle
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.runCurrent
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.test.setMain
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
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
    ): HomeViewModel = HomeViewModel(
        repository = FakeAppInfoRepository("Initial name"),
        locationClient = locationClient,
        nearbySearchRepository = nearbySearchRepository,
    )

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
    }
}
