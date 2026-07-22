package com.kltn.travelassistant.feature.poi.presentation

import androidx.lifecycle.SavedStateHandle
import com.kltn.travelassistant.feature.nearby.domain.PoiCategoryLabel
import com.kltn.travelassistant.feature.poi.domain.PoiDetail
import com.kltn.travelassistant.feature.poi.domain.PoiDetailRepository
import com.kltn.travelassistant.feature.poi.domain.PoiDetailResult
import com.kltn.travelassistant.navigation.PoiDetailDestination
import java.util.ArrayDeque
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.flow.MutableStateFlow
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
class PoiDetailViewModelTest {
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
    fun startsLoadingThenShowsContent() = runTest(dispatcher) {
        val repository = FakeRepository(PoiDetailResult.Success(detail))
        val viewModel = createViewModel(repository)

        assertEquals(PoiDetailUiState.Loading, viewModel.uiState.value)
        advanceUntilIdle()

        assertEquals(PoiDetailUiState.Content(detail), viewModel.uiState.value)
        assertEquals(listOf("poi-1" to "vi"), repository.requests)
    }

    @Test
    fun missingPoiShowsNotFound() = runTest(dispatcher) {
        val viewModel = createViewModel(FakeRepository(PoiDetailResult.NotFound))

        advanceUntilIdle()

        assertEquals(PoiDetailUiState.NotFound, viewModel.uiState.value)
    }

    @Test
    fun databaseFailureShowsError() = runTest(dispatcher) {
        val viewModel = createViewModel(FakeRepository(PoiDetailResult.DatabaseError))

        advanceUntilIdle()

        assertEquals(PoiDetailUiState.Error, viewModel.uiState.value)
    }

    @Test
    fun retryRecoversFromError() = runTest(dispatcher) {
        val repository = FakeRepository(
            PoiDetailResult.DatabaseError,
            PoiDetailResult.Success(detail),
        )
        val viewModel = createViewModel(repository)
        advanceUntilIdle()

        viewModel.retry()
        assertEquals(PoiDetailUiState.Loading, viewModel.uiState.value)
        advanceUntilIdle()

        assertEquals(PoiDetailUiState.Content(detail), viewModel.uiState.value)
        assertEquals(2, repository.requests.size)
    }

    @Test
    fun blankNavigationIdIsControlledNotFound() = runTest(dispatcher) {
        val repository = FakeRepository(PoiDetailResult.Success(detail))
        val viewModel = PoiDetailViewModel(SavedStateHandle(), repository)

        advanceUntilIdle()

        assertEquals(PoiDetailUiState.NotFound, viewModel.uiState.value)
        assertEquals(emptyList<Pair<String, String>>(), repository.requests)
    }

    @Test
    fun exposedStateIsReadOnly() = runTest(dispatcher) {
        val viewModel = createViewModel(FakeRepository(PoiDetailResult.Success(detail)))

        assertFalse(viewModel.uiState is MutableStateFlow<*>)
    }

    private fun createViewModel(repository: PoiDetailRepository) = PoiDetailViewModel(
        SavedStateHandle(mapOf(PoiDetailDestination.POI_ID_ARGUMENT to "poi-1")),
        repository,
    )

    private class FakeRepository(
        vararg results: PoiDetailResult,
    ) : PoiDetailRepository {
        private val results = ArrayDeque(results.toList())
        val requests = mutableListOf<Pair<String, String>>()

        override suspend fun getPoiDetail(
            poiId: String,
            languageCode: String,
        ): PoiDetailResult {
            requests += poiId to languageCode
            return results.removeFirst()
        }
    }

    private companion object {
        val detail = PoiDetail(
            poiId = "poi-1",
            name = "Chợ Bến Thành",
            category = PoiCategoryLabel.MARKET,
            city = "Ho Chi Minh City",
            area = null,
            address = null,
            shortDescription = null,
            menuItems = emptyList(),
            narration = null,
        )
    }
}
