package com.kltn.travelassistant.feature.downloads.presentation

import com.kltn.travelassistant.feature.downloads.domain.PackageSyncFailureCode
import com.kltn.travelassistant.feature.downloads.domain.PackageSyncPhase
import com.kltn.travelassistant.feature.downloads.domain.PackageSyncRepository
import com.kltn.travelassistant.feature.downloads.domain.PackageSyncState
import com.kltn.travelassistant.feature.downloads.domain.PackageWorkState
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.runCurrent
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.test.setMain
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Before
import org.junit.Test

@OptIn(ExperimentalCoroutinesApi::class)
class DownloadsViewModelTest {
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
    fun progressSuccessFailureAndActionsMapWithoutFakeCompletion() = runTest(dispatcher) {
        val repository = FakeRepository()
        val viewModel = DownloadsViewModel(repository)
        viewModel.uiState.value
        runCurrent()
        assertEquals(DownloadsStatus.Idle, viewModel.uiState.value.status)

        repository.emit(
            PackageSyncState(
                workState = PackageWorkState.Running(PackageSyncPhase.VERIFYING),
            ),
        )
        runCurrent()
        assertEquals(
            DownloadsStatus.InProgress(PackageSyncPhase.VERIFYING),
            viewModel.uiState.value.status,
        )

        repository.emit(PackageSyncState(workState = PackageWorkState.Succeeded))
        runCurrent()
        assertEquals(DownloadsStatus.Success, viewModel.uiState.value.status)

        repository.emit(
            PackageSyncState(
                workState = PackageWorkState.Failed(
                    PackageSyncFailureCode.CHECKSUM_MISMATCH,
                ),
            ),
        )
        runCurrent()
        assertEquals(
            DownloadsStatus.Failure(PackageSyncFailureCode.CHECKSUM_MISMATCH),
            viewModel.uiState.value.status,
        )

        viewModel.download()
        viewModel.retry()
        assertEquals(1, repository.downloadCount)
        assertEquals(1, repository.retryCount)
    }

    private class FakeRepository : PackageSyncRepository {
        private val states = MutableStateFlow(PackageSyncState())
        var downloadCount = 0
        var retryCount = 0

        override fun observeHcmcSync(): Flow<PackageSyncState> = states

        override fun startHcmcDownload() {
            downloadCount += 1
        }

        override fun retryHcmcDownload() {
            retryCount += 1
        }

        fun emit(state: PackageSyncState) {
            states.value = state
        }
    }
}
