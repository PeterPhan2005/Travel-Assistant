package com.kltn.travelassistant.feature.appshell.presentation

import com.kltn.travelassistant.data.connectivity.ConnectivityObserver
import com.kltn.travelassistant.data.connectivity.ConnectivityStatus
import com.kltn.travelassistant.feature.appshell.domain.LocalTravelPackageMetadata
import com.kltn.travelassistant.feature.appshell.domain.LocalTravelPackageRepository
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.flow
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.runCurrent
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.test.setMain
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test

@OptIn(ExperimentalCoroutinesApi::class)
class AppShellViewModelTest {
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
    fun initialStateIsCheckingAndPackageLoading() = runTest(dispatcher) {
        val viewModel = createViewModel()

        assertEquals(AppShellUiState(), viewModel.uiState.value)
    }

    @Test
    fun connectivityTransitionsThroughUnknownOnlineAndOffline() = runTest(dispatcher) {
        val connectivity = FakeConnectivityObserver()
        val viewModel = createViewModel(connectivity = connectivity)
        runCurrent()
        assertEquals(ConnectivityUiState.Checking, viewModel.uiState.value.connectivity)

        connectivity.emit(ConnectivityStatus.ONLINE)
        runCurrent()
        assertEquals(ConnectivityUiState.Online, viewModel.uiState.value.connectivity)

        connectivity.emit(ConnectivityStatus.OFFLINE)
        runCurrent()
        assertEquals(ConnectivityUiState.Offline, viewModel.uiState.value.connectivity)
    }

    @Test
    fun offlineDismissalAppliesOnlyToCurrentOfflineEpisode() = runTest(dispatcher) {
        val connectivity = FakeConnectivityObserver(ConnectivityStatus.OFFLINE)
        val viewModel = createViewModel(
            connectivity = connectivity,
            packages = FakeLocalTravelPackageRepository(metadata),
        )
        runCurrent()

        assertEquals(ConnectivityUiState.Offline, viewModel.uiState.value.connectivity)
        assertTrue(viewModel.uiState.value.shouldShowOfflineWarning)
        assertFalse(viewModel.uiState.value.isOfflineWarningDismissed)
        val packageBeforeDismissal = viewModel.uiState.value.localPackage

        viewModel.dismissOfflineWarning()
        runCurrent()

        assertEquals(ConnectivityUiState.Offline, viewModel.uiState.value.connectivity)
        assertTrue(viewModel.uiState.value.isOfflineWarningDismissed)
        assertFalse(viewModel.uiState.value.shouldShowOfflineWarning)
        assertEquals(packageBeforeDismissal, viewModel.uiState.value.localPackage)

        connectivity.emit(ConnectivityStatus.ONLINE)
        runCurrent()

        assertEquals(ConnectivityUiState.Online, viewModel.uiState.value.connectivity)
        assertFalse(viewModel.uiState.value.isOfflineWarningDismissed)
        assertFalse(viewModel.uiState.value.shouldShowOfflineWarning)

        connectivity.emit(ConnectivityStatus.OFFLINE)
        runCurrent()

        assertEquals(ConnectivityUiState.Offline, viewModel.uiState.value.connectivity)
        assertFalse(viewModel.uiState.value.isOfflineWarningDismissed)
        assertTrue(viewModel.uiState.value.shouldShowOfflineWarning)
    }

    @Test
    fun packageTransitionsThroughLoadingUnavailableAndAvailable() = runTest(dispatcher) {
        val packages = FakeLocalTravelPackageRepository()
        val viewModel = createViewModel(packages = packages)
        assertEquals(LocalPackageUiState.Loading, viewModel.uiState.value.localPackage)

        runCurrent()
        assertEquals(LocalPackageUiState.Unavailable, viewModel.uiState.value.localPackage)

        packages.emit(metadata)
        runCurrent()
        assertEquals(
            LocalPackageUiState.Available(
                version = metadata.version,
                publishedAtEpochMillis = metadata.publishedAtEpochMillis,
            ),
            viewModel.uiState.value.localPackage,
        )
    }

    @Test
    fun packageFailureDoesNotMarkOnlineConnectivityOffline() = runTest(dispatcher) {
        val viewModel = AppShellViewModel(
            connectivityObserver = FakeConnectivityObserver(ConnectivityStatus.ONLINE),
            localTravelPackageRepository = FailingLocalTravelPackageRepository(),
        )

        runCurrent()

        assertEquals(ConnectivityUiState.Online, viewModel.uiState.value.connectivity)
        assertEquals(LocalPackageUiState.Error, viewModel.uiState.value.localPackage)
    }

    @Test
    fun connectivityFailureDoesNotHideAvailableLocalPackage() = runTest(dispatcher) {
        val viewModel = AppShellViewModel(
            connectivityObserver = FailingConnectivityObserver(),
            localTravelPackageRepository = FakeLocalTravelPackageRepository(metadata),
        )

        runCurrent()

        assertEquals(ConnectivityUiState.Checking, viewModel.uiState.value.connectivity)
        assertEquals(
            LocalPackageUiState.Available(
                version = metadata.version,
                publishedAtEpochMillis = metadata.publishedAtEpochMillis,
            ),
            viewModel.uiState.value.localPackage,
        )
    }

    @Test
    fun blankPackageVersionIsUnavailableWithoutFabrication() = runTest(dispatcher) {
        val packages = FakeLocalTravelPackageRepository(metadata.copy(version = " "))
        val viewModel = createViewModel(packages = packages)

        runCurrent()

        assertEquals(LocalPackageUiState.Unavailable, viewModel.uiState.value.localPackage)
    }

    @Test
    fun publicStateIsImmutable() = runTest(dispatcher) {
        val viewModel = createViewModel()

        assertFalse(viewModel.uiState is MutableStateFlow<*>)
    }

    private fun createViewModel(
        connectivity: ConnectivityObserver = FakeConnectivityObserver(),
        packages: LocalTravelPackageRepository = FakeLocalTravelPackageRepository(),
    ) = AppShellViewModel(
        connectivityObserver = connectivity,
        localTravelPackageRepository = packages,
    )

    private class FakeConnectivityObserver(
        initialStatus: ConnectivityStatus = ConnectivityStatus.UNKNOWN,
    ) : ConnectivityObserver {
        private val mutableStatus = MutableStateFlow(initialStatus)
        override val status: StateFlow<ConnectivityStatus> = mutableStatus

        fun emit(status: ConnectivityStatus) {
            mutableStatus.value = status
        }
    }

    private class FailingConnectivityObserver : ConnectivityObserver {
        override val status: Flow<ConnectivityStatus> = flow {
            error("connectivity unavailable")
        }
    }

    private class FakeLocalTravelPackageRepository(
        initialMetadata: LocalTravelPackageMetadata? = null,
    ) : LocalTravelPackageRepository {
        private val packages = MutableStateFlow(initialMetadata)

        override fun observeLatestHcmcPackage(): Flow<LocalTravelPackageMetadata?> = packages

        fun emit(metadata: LocalTravelPackageMetadata?) {
            packages.value = metadata
        }
    }

    private class FailingLocalTravelPackageRepository : LocalTravelPackageRepository {
        override fun observeLatestHcmcPackage(): Flow<LocalTravelPackageMetadata?> = flow {
            error("package unavailable")
        }
    }

    private companion object {
        val metadata = LocalTravelPackageMetadata(
            version = "2026.07.1",
            publishedAtEpochMillis = 1_721_510_400_000L,
        )
    }
}
