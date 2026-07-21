package com.kltn.travelassistant.feature.home.presentation

import com.kltn.travelassistant.data.repository.AppInfoRepository
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.advanceUntilIdle
import kotlinx.coroutines.test.resetMain
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
    fun initialUiStateUsesRepositorySnapshot() = runTest(dispatcher) {
        val viewModel = HomeViewModel(FakeAppInfoRepository("Initial name"))

        assertEquals(HomeUiState(appName = "Initial name"), viewModel.uiState.value)
    }

    @Test
    fun repositoryStateChangesReachUiState() = runTest(dispatcher) {
        val repository = FakeAppInfoRepository("Initial name")
        val viewModel = HomeViewModel(repository)

        repository.updateAppName("Updated name")
        advanceUntilIdle()

        assertEquals(HomeUiState(appName = "Updated name"), viewModel.uiState.value)
    }

    @Test
    fun exposedUiStateIsNotMutableStateFlow() = runTest(dispatcher) {
        val viewModel = HomeViewModel(FakeAppInfoRepository("Initial name"))

        assertFalse(viewModel.uiState is MutableStateFlow<*>)
    }

    private class FakeAppInfoRepository(initialAppName: String) : AppInfoRepository {
        private val mutableAppName = MutableStateFlow(initialAppName)

        override val appName: StateFlow<String> = mutableAppName.asStateFlow()

        fun updateAppName(appName: String) {
            mutableAppName.value = appName
        }
    }
}
