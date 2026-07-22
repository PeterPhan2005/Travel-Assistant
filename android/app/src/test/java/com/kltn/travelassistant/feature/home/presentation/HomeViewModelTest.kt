package com.kltn.travelassistant.feature.home.presentation

import com.kltn.travelassistant.data.location.DeviceLocation
import com.kltn.travelassistant.data.location.LocationAcquisitionResult
import com.kltn.travelassistant.data.location.LocationClient
import com.kltn.travelassistant.data.repository.AppInfoRepository
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
        val viewModel = createViewModel(locationClient = locationClient)

        viewModel.onLocationPermissionGranted()
        assertEquals(LocationUiState.Loading, viewModel.uiState.value.locationState)
        advanceUntilIdle()

        assertEquals(LocationUiState.Available(testLocation), viewModel.uiState.value.locationState)
        assertEquals(1, locationClient.requestCount)
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
        val viewModel = HomeViewModel(repository, FakeLocationClient(successResult))

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

    private fun createViewModel(
        locationClient: LocationClient = FakeLocationClient(successResult),
    ): HomeViewModel = HomeViewModel(
        repository = FakeAppInfoRepository("Initial name"),
        locationClient = locationClient,
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

    private companion object {
        val testLocation = DeviceLocation(
            latitude = 10.7799,
            longitude = 106.7,
            accuracyMeters = 12.5f,
            capturedAtEpochMillis = 1_753_200_000_000L,
        )
        val successResult = LocationAcquisitionResult.Success(testLocation)
    }
}
