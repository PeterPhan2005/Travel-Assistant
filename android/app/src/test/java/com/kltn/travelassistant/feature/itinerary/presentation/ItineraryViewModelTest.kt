package com.kltn.travelassistant.feature.itinerary.presentation

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.ViewModelStore
import androidx.lifecycle.ViewModelStoreOwner
import com.kltn.travelassistant.analytics.ItineraryCreationOutcome
import com.kltn.travelassistant.analytics.ItineraryFailureCategory
import com.kltn.travelassistant.analytics.ProductAnalytics
import com.kltn.travelassistant.analytics.ProductAnalyticsEvent
import com.kltn.travelassistant.feature.itinerary.data.ItineraryJsonCodec
import com.kltn.travelassistant.feature.itinerary.domain.ItineraryCity
import com.kltn.travelassistant.feature.itinerary.domain.ItineraryDraft
import com.kltn.travelassistant.feature.itinerary.domain.ItineraryDraftFailure
import com.kltn.travelassistant.feature.itinerary.domain.ItineraryDraftGenerationResult
import com.kltn.travelassistant.feature.itinerary.domain.ItineraryDraftGenerator
import com.kltn.travelassistant.feature.itinerary.domain.ItineraryDraftItem
import com.kltn.travelassistant.feature.itinerary.domain.ItineraryDraftRequest
import com.kltn.travelassistant.feature.itinerary.domain.ItineraryDraftWarning
import com.kltn.travelassistant.feature.itinerary.domain.ItineraryLocationSnapshot
import com.kltn.travelassistant.feature.itinerary.domain.ItinerarySaveBoundary
import com.kltn.travelassistant.feature.itinerary.domain.ItinerarySaveResult
import com.kltn.travelassistant.feature.itinerary.domain.ItinerarySyncState
import com.kltn.travelassistant.feature.itinerary.domain.SavedItinerary
import com.kltn.travelassistant.feature.itinerary.domain.SavedItineraryDeleteResult
import com.kltn.travelassistant.feature.itinerary.domain.SavedItineraryLibraryState
import com.kltn.travelassistant.feature.itinerary.domain.SavedItineraryRepository
import com.kltn.travelassistant.feature.itinerary.readItineraryContractFixture
import java.time.LocalDate
import java.time.LocalTime
import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.Job
import kotlinx.coroutines.NonCancellable
import kotlinx.coroutines.awaitCancellation
import kotlinx.coroutines.currentCoroutineContext
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flowOf
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.advanceUntilIdle
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.test.setMain
import kotlinx.coroutines.withContext
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test

@OptIn(ExperimentalCoroutinesApi::class)
class ItineraryViewModelTest {
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
    fun invalidFormStartsNoGeneratorCall() {
        val generator = FakeGenerator(success())
        val viewModel = viewModel(generator)

        viewModel.generate(null)

        assertTrue(viewModel.uiState.value.fieldErrors.hasErrors)
        assertTrue(generator.requests.isEmpty())
    }

    @Test
    fun offlineGenerateAndRetryPreserveFormWithoutStartingGenerator() = runTest {
        val generator = FakeGenerator(success())
        val viewModel = viewModel(generator)
        enterValidForm(viewModel)

        viewModel.generate(currentLocation = null, isOnline = false)
        advanceUntilIdle()
        viewModel.retry(isOnline = false)
        advanceUntilIdle()

        assertTrue(generator.requests.isEmpty())
        assertEquals("2026-08-01", viewModel.uiState.value.form.localDate)
        assertEquals(
            ItineraryGenerationUiState.Error(ItineraryDraftFailure.OFFLINE),
            viewModel.uiState.value.generationState,
        )
    }

    @Test
    fun validRequestMapsExactlyWithAbsentOrPresentMemoryLocation() = runTest {
        val generator = FakeGenerator(success())
        val viewModel = viewModel(generator)
        enterValidForm(viewModel)

        viewModel.generate(null)
        advanceUntilIdle()

        assertNull(generator.requests.single().currentLocation)
        assertEquals(request(), generator.requests.single())

        viewModel.onCitySelected(ItineraryCity.BANGKOK)
        val location = ItineraryLocationSnapshot(13.7563, 100.5018)
        generator.result = success(
            draft().copy(
                city = ItineraryCity.BANGKOK,
                timezone = "Asia/Bangkok",
            ),
        )
        viewModel.generate(location)
        advanceUntilIdle()

        assertEquals(location, generator.requests.last().currentLocation)
        assertEquals("Asia/Bangkok", generator.requests.last().timezone)
    }

    @Test
    fun loadingIsVisibleAndDuplicateGenerateIsIgnored() = runTest {
        val gate = CompletableDeferred<ItineraryDraftGenerationResult>()
        val generator = FakeGenerator(gate = gate)
        val analytics = RecordingProductAnalytics()
        val viewModel = viewModel(generator, analytics = analytics)
        enterValidForm(viewModel)

        viewModel.generate(null)
        dispatcher.scheduler.runCurrent()
        viewModel.generate(null)

        assertEquals(ItineraryGenerationUiState.Loading, viewModel.uiState.value.generationState)
        assertEquals(1, generator.requests.size)
        assertEquals(
            listOf(
                ProductAnalyticsEvent.ItineraryCreation(
                    ItineraryCreationOutcome.ATTEMPTED,
                ),
            ),
            analytics.events,
        )
    }

    @Test
    fun successPreservesPartialWarningsAndNeverAutoSaves() = runTest {
        val save = FakeSaveBoundary()
        val expected = draft().copy(
            warnings = listOf(
                ItineraryDraftWarning("Thiếu dữ liệu thời gian di chuyển."),
                ItineraryDraftWarning("Hãy kiểm tra giờ mở cửa."),
            ),
        )
        val analytics = RecordingProductAnalytics()
        val viewModel = viewModel(FakeGenerator(success(expected)), save, analytics = analytics)
        enterValidForm(viewModel)

        viewModel.generate(null)
        advanceUntilIdle()

        assertEquals(
            ItineraryGenerationUiState.Content(expected),
            viewModel.uiState.value.generationState,
        )
        assertTrue(save.drafts.isEmpty())
        assertEquals(
            listOf(
                ProductAnalyticsEvent.ItineraryCreation(ItineraryCreationOutcome.ATTEMPTED),
                ProductAnalyticsEvent.ItineraryCreation(ItineraryCreationOutcome.SUCCEEDED),
            ),
            analytics.events,
        )
    }

    @Test
    fun exactBackendProducedHcmcSuccessReachesContent() = runTest {
        val decoded = ItineraryJsonCodec().decodeResponse(
            readItineraryContractFixture("t062_itinerary_success_hcmc.json"),
        )
        val viewModel = viewModel(FakeGenerator(decoded))
        viewModel.onCitySelected(ItineraryCity.HO_CHI_MINH_CITY)
        viewModel.onLocalDateChanged("2026-08-02")
        viewModel.onStartTimeChanged("09:00")
        viewModel.onEndTimeChanged("17:00")
        viewModel.onMaximumStopsChanged("2")

        viewModel.generate(null)
        advanceUntilIdle()

        val content = viewModel.uiState.value.generationState as
            ItineraryGenerationUiState.Content
        assertEquals(LocalDate.of(2026, 8, 2), content.draft.localDate)
        assertEquals(2, content.draft.items.size)
    }

    @Test
    fun mismatchedTimelineMapsToNonRetryableInvalidResponse() = runTest {
        val mismatched = draft().copy(localDate = LocalDate.of(2026, 8, 2))
        val analytics = RecordingProductAnalytics()
        val viewModel = viewModel(FakeGenerator(success(mismatched)), analytics = analytics)
        enterValidForm(viewModel)

        viewModel.generate(null)
        advanceUntilIdle()

        assertEquals(
            ItineraryGenerationUiState.Error(ItineraryDraftFailure.INVALID_RESPONSE),
            viewModel.uiState.value.generationState,
        )
        assertEquals(
            ProductAnalyticsEvent.ItineraryCreation(
                ItineraryCreationOutcome.FAILED,
                ItineraryFailureCategory.INVALID_RESPONSE,
            ),
            analytics.events.last(),
        )
    }

    @Test
    fun retryableFailureWaitsForExplicitRetryAndUsesImmutableSnapshot() = runTest {
        val generator = QueueGenerator(
            mutableListOf(
                failure(ItineraryDraftFailure.TIMEOUT),
                success(),
            ),
        )
        val analytics = RecordingProductAnalytics()
        val viewModel = viewModel(generator, analytics = analytics)
        enterValidForm(viewModel)

        viewModel.generate(null)
        advanceUntilIdle()
        assertEquals(1, generator.requests.size)
        assertEquals("2026-08-01", viewModel.uiState.value.form.localDate)
        assertEquals(
            ItineraryGenerationUiState.Error(ItineraryDraftFailure.TIMEOUT),
            viewModel.uiState.value.generationState,
        )

        advanceUntilIdle()
        assertEquals(1, generator.requests.size)
        viewModel.retry()
        advanceUntilIdle()

        assertEquals(2, generator.requests.size)
        assertEquals(generator.requests[0], generator.requests[1])
        assertEquals(
            listOf(
                ProductAnalyticsEvent.ItineraryCreation(ItineraryCreationOutcome.ATTEMPTED),
                ProductAnalyticsEvent.ItineraryCreation(
                    ItineraryCreationOutcome.FAILED,
                    ItineraryFailureCategory.TIMEOUT,
                ),
                ProductAnalyticsEvent.ItineraryCreation(ItineraryCreationOutcome.ATTEMPTED),
                ProductAnalyticsEvent.ItineraryCreation(ItineraryCreationOutcome.SUCCEEDED),
            ),
            analytics.events,
        )
    }

    @Test
    fun nonRetryableFailureAndUnsupportedTransportCannotRetry() = runTest {
        listOf(
            ItineraryDraftFailure.INVALID_REQUEST,
            ItineraryDraftFailure.UNSUPPORTED_TRANSPORT,
        ).forEach { failure ->
            val generator = FakeGenerator(failure(failure))
            val viewModel = viewModel(generator)
            enterValidForm(viewModel)

            viewModel.generate(null)
            advanceUntilIdle()
            viewModel.retry()
            advanceUntilIdle()

            assertEquals(1, generator.requests.size)
            if (failure == ItineraryDraftFailure.UNSUPPORTED_TRANSPORT) {
                assertEquals(
                    ItineraryGenerationUiState.Unavailable,
                    viewModel.uiState.value.generationState,
                )
            }
        }
    }

    @Test
    fun explicitCancellationPreservesFormAndLateResultIsIgnored() = runTest {
        val gate = CompletableDeferred<ItineraryDraftGenerationResult>()
        val generator = FakeGenerator(gate = gate, ignoreCancellation = true)
        val analytics = RecordingProductAnalytics()
        val viewModel = viewModel(generator, analytics = analytics)
        enterValidForm(viewModel)
        viewModel.generate(null)
        dispatcher.scheduler.runCurrent()

        viewModel.cancelGeneration()
        gate.complete(success())
        advanceUntilIdle()

        assertEquals(
            ItineraryGenerationUiState.Cancelled,
            viewModel.uiState.value.generationState,
        )
        assertEquals("2026-08-01", viewModel.uiState.value.form.localDate)
        assertEquals(
            listOf(
                ProductAnalyticsEvent.ItineraryCreation(ItineraryCreationOutcome.ATTEMPTED),
                ProductAnalyticsEvent.ItineraryCreation(ItineraryCreationOutcome.CANCELLED),
            ),
            analytics.events,
        )
    }

    @Test
    fun openingSavedTripEmitsOncePerExplicitReturnAndSignedOutStateEmitsNothing() = runTest {
        val analytics = RecordingProductAnalytics()
        val saved = SavedItinerary(
            id = "itinerary-1",
            title = "Một ngày ở TP.HCM",
            draft = draft(),
            syncState = ItinerarySyncState.PENDING,
        )
        val viewModel = viewModel(
            generator = FakeGenerator(success()),
            savedRepository = FakeSavedRepository(
                SavedItineraryLibraryState.Content(listOf(saved)),
            ),
            analytics = analytics,
        )
        advanceUntilIdle()

        viewModel.openSavedItinerary(saved.id)
        viewModel.openSavedItinerary(saved.id)
        viewModel.returnToGeneration()
        viewModel.openSavedItinerary(saved.id)

        assertEquals(
            listOf(ProductAnalyticsEvent.TripReturn, ProductAnalyticsEvent.TripReturn),
            analytics.events,
        )

        val signedOut = viewModel(
            generator = FakeGenerator(success()),
            savedRepository = FakeSavedRepository(SavedItineraryLibraryState.SignedOut),
            analytics = analytics,
        )
        advanceUntilIdle()
        signedOut.openSavedItinerary(saved.id)
        assertEquals(2, analytics.events.size)
    }

    @Test
    fun editingCancelsLoadingAndClearsAStalePreview() = runTest {
        val gate = CompletableDeferred<ItineraryDraftGenerationResult>()
        val viewModel = viewModel(FakeGenerator(gate = gate))
        enterValidForm(viewModel)
        viewModel.generate(null)
        dispatcher.scheduler.runCurrent()

        viewModel.onMaximumStopsChanged("3")
        assertEquals(
            ItineraryGenerationUiState.Cancelled,
            viewModel.uiState.value.generationState,
        )
        assertEquals("3", viewModel.uiState.value.form.maximumStops)

        val completedViewModel = viewModel(FakeGenerator(success()))
        enterValidForm(completedViewModel)
        completedViewModel.generate(null)
        advanceUntilIdle()
        completedViewModel.onNotesChanged("Nhu cầu mới")

        assertEquals(
            ItineraryGenerationUiState.Idle,
            completedViewModel.uiState.value.generationState,
        )
    }

    @Test
    fun screenDepartureAndBackgroundCancelWithoutAutomaticRestart() = runTest {
        val generator = CancellableGenerator()
        val viewModel = viewModel(generator)
        enterValidForm(viewModel)
        viewModel.generate(null)
        dispatcher.scheduler.runCurrent()

        viewModel.onScreenLeft()
        dispatcher.scheduler.runCurrent()
        viewModel.onScreenLeft()
        viewModel.onAppBackgrounded()

        assertEquals(1, generator.cancellations)
        assertEquals(1, generator.requests.size)
        assertEquals(
            ItineraryGenerationUiState.Cancelled,
            viewModel.uiState.value.generationState,
        )
    }

    @Test
    fun clearingViewModelCancelsActiveGeneration() = runTest {
        val generator = CancellableGenerator()
        val save = FakeSaveBoundary()
        val store = ViewModelStore()
        val owner = object : ViewModelStoreOwner {
            override val viewModelStore: ViewModelStore = store
        }
        val provider = ViewModelProvider(
            owner,
            object : ViewModelProvider.Factory {
                @Suppress("UNCHECKED_CAST")
                override fun <T : ViewModel> create(modelClass: Class<T>): T =
                    ItineraryViewModel(generator, save) as T
            },
        )
        val viewModel = provider[ItineraryViewModel::class.java]
        enterValidForm(viewModel)
        viewModel.generate(null)
        dispatcher.scheduler.runCurrent()

        store.clear()
        dispatcher.scheduler.runCurrent()

        assertEquals(1, generator.cancellations)
    }

    @Test
    fun saveRequiresDraftAndOneExplicitTapInvokesBoundaryExactlyOnce() = runTest {
        val save = FakeSaveBoundary(result = ItinerarySaveResult.SavedLocally)
        val viewModel = viewModel(FakeGenerator(success()), save)

        viewModel.save()
        assertTrue(save.drafts.isEmpty())
        enterValidForm(viewModel)
        viewModel.generate(null)
        advanceUntilIdle()
        assertTrue(save.drafts.isEmpty())

        viewModel.save()
        advanceUntilIdle()

        assertEquals(listOf(draft()), save.drafts)
        assertEquals(
            ItinerarySaveUiState.SavedLocallyPendingSync,
            viewModel.uiState.value.saveState,
        )
    }

    @Test
    fun regenerationInvalidatesOldSaveBeforeDisplayingNewDraft() = runTest {
        val oldDraft = draft()
        val newDraft = draft().copy(
            items = draft().items.mapIndexed { index, item ->
                if (index == 0) item.copy(title = "Bưu điện — bản nháp B") else item
            },
        )
        val generator = QueueGenerator(
            mutableListOf(success(oldDraft), success(newDraft)),
        )
        val oldSaveGate = CompletableDeferred<ItinerarySaveResult>()
        val save = NonCancellableSaveBoundary(mutableListOf(oldSaveGate))
        val viewModel = viewModel(generator, save)
        enterValidForm(viewModel)
        viewModel.generate(null)
        advanceUntilIdle()

        viewModel.save()
        dispatcher.scheduler.runCurrent()
        assertEquals(ItinerarySaveUiState.Saving, viewModel.uiState.value.saveState)

        viewModel.generate(null)
        assertEquals(
            ItineraryGenerationUiState.Loading,
            viewModel.uiState.value.generationState,
        )
        assertEquals(ItinerarySaveUiState.Idle, viewModel.uiState.value.saveState)
        advanceUntilIdle()
        assertEquals(
            ItineraryGenerationUiState.Content(newDraft),
            viewModel.uiState.value.generationState,
        )

        oldSaveGate.complete(ItinerarySaveResult.SavedLocally)
        advanceUntilIdle()

        assertEquals(1, save.cancelledCalls)
        assertEquals(
            ItineraryGenerationUiState.Content(newDraft),
            viewModel.uiState.value.generationState,
        )
        assertEquals(ItinerarySaveUiState.Idle, viewModel.uiState.value.saveState)
    }

    @Test
    fun regenerationWithoutActiveSaveReplacesDraftAndKeepsSaveIdle() = runTest {
        val newDraft = draft().copy(
            warnings = listOf(ItineraryDraftWarning("Cảnh báo của bản nháp B")),
        )
        val generator = QueueGenerator(
            mutableListOf(success(), success(newDraft)),
        )
        val viewModel = viewModel(generator)
        enterValidForm(viewModel)

        viewModel.generate(null)
        advanceUntilIdle()
        viewModel.generate(null)
        advanceUntilIdle()

        assertEquals(2, generator.requests.size)
        assertEquals(
            ItineraryGenerationUiState.Content(newDraft),
            viewModel.uiState.value.generationState,
        )
        assertEquals(ItinerarySaveUiState.Idle, viewModel.uiState.value.saveState)
    }

    @Test
    fun navigationInvalidatesSaveAndIgnoresNonCancellableLateResult() = runTest {
        val gate = CompletableDeferred<ItinerarySaveResult>()
        val save = NonCancellableSaveBoundary(mutableListOf(gate))
        val viewModel = viewModel(FakeGenerator(success()), save)
        generateDraft(viewModel)

        viewModel.save()
        dispatcher.scheduler.runCurrent()
        viewModel.onScreenLeft()
        gate.complete(ItinerarySaveResult.SavedLocally)
        advanceUntilIdle()

        assertEquals(ItinerarySaveUiState.Idle, viewModel.uiState.value.saveState)
    }

    @Test
    fun backgroundInvalidatesSaveAndIgnoresNonCancellableLateResult() = runTest {
        val gate = CompletableDeferred<ItinerarySaveResult>()
        val save = NonCancellableSaveBoundary(mutableListOf(gate))
        val viewModel = viewModel(FakeGenerator(success()), save)
        generateDraft(viewModel)

        viewModel.save()
        dispatcher.scheduler.runCurrent()
        viewModel.onAppBackgrounded()
        gate.complete(ItinerarySaveResult.AuthenticationRequired)
        advanceUntilIdle()

        assertEquals(ItinerarySaveUiState.Idle, viewModel.uiState.value.saveState)
    }

    @Test
    fun editingInvalidatesSaveAndIgnoresNonCancellableLateResult() = runTest {
        val gate = CompletableDeferred<ItinerarySaveResult>()
        val save = NonCancellableSaveBoundary(mutableListOf(gate))
        val viewModel = viewModel(FakeGenerator(success()), save)
        generateDraft(viewModel)

        viewModel.save()
        dispatcher.scheduler.runCurrent()
        viewModel.onNotesChanged("Nhu cầu mới")
        gate.complete(ItinerarySaveResult.Failed)
        advanceUntilIdle()

        assertEquals(ItinerarySaveUiState.Idle, viewModel.uiState.value.saveState)
        assertEquals("Nhu cầu mới", viewModel.uiState.value.form.notes)
    }

    @Test
    fun oldSaveResultCannotOverwriteNewerSaveAttempt() = runTest {
        val oldGate = CompletableDeferred<ItinerarySaveResult>()
        val newGate = CompletableDeferred<ItinerarySaveResult>()
        val save = NonCancellableSaveBoundary(mutableListOf(oldGate, newGate))
        val viewModel = viewModel(FakeGenerator(success()), save)
        generateDraft(viewModel)

        viewModel.save()
        dispatcher.scheduler.runCurrent()
        viewModel.onNotesChanged("Nhu cầu mới")
        viewModel.generate(null)
        advanceUntilIdle()
        viewModel.save()
        dispatcher.scheduler.runCurrent()

        newGate.complete(ItinerarySaveResult.SavedLocally)
        advanceUntilIdle()
        assertEquals(
            ItinerarySaveUiState.SavedLocallyPendingSync,
            viewModel.uiState.value.saveState,
        )

        oldGate.complete(ItinerarySaveResult.SavedLocally)
        advanceUntilIdle()
        assertEquals(
            ItinerarySaveUiState.SavedLocallyPendingSync,
            viewModel.uiState.value.saveState,
        )
    }

    @Test
    fun clearingViewModelCancelsActiveSaveAndIgnoresLateResult() = runTest {
        val gate = CompletableDeferred<ItinerarySaveResult>()
        val save = NonCancellableSaveBoundary(mutableListOf(gate))
        val store = ViewModelStore()
        val owner = object : ViewModelStoreOwner {
            override val viewModelStore: ViewModelStore = store
        }
        val provider = ViewModelProvider(
            owner,
            object : ViewModelProvider.Factory {
                @Suppress("UNCHECKED_CAST")
                override fun <T : ViewModel> create(modelClass: Class<T>): T =
                    ItineraryViewModel(FakeGenerator(success()), save) as T
            },
        )
        val viewModel = provider[ItineraryViewModel::class.java]
        generateDraft(viewModel)

        viewModel.save()
        dispatcher.scheduler.runCurrent()
        store.clear()
        gate.complete(ItinerarySaveResult.SavedLocally)
        advanceUntilIdle()

        assertEquals(1, save.cancelledCalls)
        assertEquals(ItinerarySaveUiState.Idle, viewModel.uiState.value.saveState)
    }

    @Test
    fun duplicateSaveWhileActiveIsIgnoredAndRecreationNeverAutoSaves() = runTest {
        val gate = CompletableDeferred<ItinerarySaveResult>()
        val save = NonCancellableSaveBoundary(mutableListOf(gate))
        val first = viewModel(FakeGenerator(success()), save)
        generateDraft(first)

        first.save()
        dispatcher.scheduler.runCurrent()
        first.save()
        assertEquals(1, save.drafts.size)

        val recreated = viewModel(FakeGenerator(success()), save)
        advanceUntilIdle()
        recreated.onScreenLeft()
        assertEquals(1, save.drafts.size)
        assertEquals(ItineraryUiState(), recreated.uiState.value)

        first.onScreenLeft()
        gate.complete(ItinerarySaveResult.AuthenticationRequired)
        advanceUntilIdle()
        assertEquals(ItinerarySaveUiState.Idle, first.uiState.value.saveState)
    }

    private fun viewModel(
        generator: ItineraryDraftGenerator,
        save: ItinerarySaveBoundary = FakeSaveBoundary(),
        savedRepository: SavedItineraryRepository = FakeSavedRepository(
            SavedItineraryLibraryState.Loading,
        ),
        analytics: ProductAnalytics = RecordingProductAnalytics(),
    ) = ItineraryViewModel(generator, save, savedRepository, analytics)

    private fun enterValidForm(viewModel: ItineraryViewModel) {
        viewModel.onCitySelected(ItineraryCity.HO_CHI_MINH_CITY)
        viewModel.onLocalDateChanged("2026-08-01")
        viewModel.onStartTimeChanged("09:00")
        viewModel.onEndTimeChanged("17:00")
        viewModel.onMaximumStopsChanged("4")
    }

    private fun generateDraft(viewModel: ItineraryViewModel) {
        enterValidForm(viewModel)
        viewModel.generate(null)
        dispatcher.scheduler.advanceUntilIdle()
    }

    private class FakeGenerator(
        var result: ItineraryDraftGenerationResult? = null,
        private val gate: CompletableDeferred<ItineraryDraftGenerationResult>? = null,
        private val ignoreCancellation: Boolean = false,
    ) : ItineraryDraftGenerator {
        val requests = mutableListOf<ItineraryDraftRequest>()

        override suspend fun generate(
            request: ItineraryDraftRequest,
        ): ItineraryDraftGenerationResult {
            requests += request
            val deferred = gate
            if (deferred != null) {
                return if (ignoreCancellation) {
                    withContext(NonCancellable) { deferred.await() }
                } else {
                    deferred.await()
                }
            }
            return requireNotNull(result)
        }
    }

    private class QueueGenerator(
        private val results: MutableList<ItineraryDraftGenerationResult>,
    ) : ItineraryDraftGenerator {
        val requests = mutableListOf<ItineraryDraftRequest>()

        override suspend fun generate(
            request: ItineraryDraftRequest,
        ): ItineraryDraftGenerationResult {
            requests += request
            return results.removeAt(0)
        }
    }

    private class CancellableGenerator : ItineraryDraftGenerator {
        val requests = mutableListOf<ItineraryDraftRequest>()
        var cancellations = 0

        override suspend fun generate(
            request: ItineraryDraftRequest,
        ): ItineraryDraftGenerationResult {
            requests += request
            try {
                awaitCancellation()
            } finally {
                cancellations += 1
            }
        }
    }

    private class FakeSaveBoundary(
        private val result: ItinerarySaveResult = ItinerarySaveResult.SavedLocally,
        private val gate: CompletableDeferred<ItinerarySaveResult>? = null,
    ) : ItinerarySaveBoundary {
        val drafts = mutableListOf<ItineraryDraft>()

        override suspend fun save(draft: ItineraryDraft): ItinerarySaveResult {
            drafts += draft
            return gate?.await() ?: result
        }
    }

    private class NonCancellableSaveBoundary(
        private val gates: MutableList<CompletableDeferred<ItinerarySaveResult>>,
    ) : ItinerarySaveBoundary {
        val drafts = mutableListOf<ItineraryDraft>()
        var cancelledCalls = 0
        private var nextGateIndex = 0

        override suspend fun save(draft: ItineraryDraft): ItinerarySaveResult {
            drafts += draft
            currentCoroutineContext()[Job]?.invokeOnCompletion { cause ->
                if (cause is CancellationException) cancelledCalls += 1
            }
            val gate = gates[nextGateIndex++]
            var completedResult: ItinerarySaveResult? = null
            return try {
                withContext(NonCancellable) {
                    gate.await().also { completedResult = it }
                }
            } catch (_: CancellationException) {
                requireNotNull(completedResult)
            }
        }
    }

    private class FakeSavedRepository(
        private val state: SavedItineraryLibraryState,
    ) : SavedItineraryRepository {
        override fun observeLibrary(): Flow<SavedItineraryLibraryState> = flowOf(state)

        override suspend fun delete(itineraryId: String): SavedItineraryDeleteResult =
            SavedItineraryDeleteResult.NotFound
    }

    private class RecordingProductAnalytics : ProductAnalytics {
        val events = mutableListOf<ProductAnalyticsEvent>()

        override fun track(event: ProductAnalyticsEvent) {
            events += event
        }
    }

    private fun success(
        draft: ItineraryDraft = draft(),
    ) = ItineraryDraftGenerationResult.Success(draft)

    private fun failure(
        reason: ItineraryDraftFailure,
    ) = ItineraryDraftGenerationResult.Failure(reason)

    private fun request() = ItineraryDraftRequest(
        city = ItineraryCity.HO_CHI_MINH_CITY,
        localDate = LocalDate.of(2026, 8, 1),
        timezone = "Asia/Ho_Chi_Minh",
        startLocalTime = LocalTime.of(9, 0),
        endLocalTime = LocalTime.of(17, 0),
        maximumStops = 4,
        notes = null,
        currentLocation = null,
    )

    private fun draft() = ItineraryDraft(
        city = ItineraryCity.HO_CHI_MINH_CITY,
        localDate = LocalDate.of(2026, 8, 1),
        timezone = "Asia/Ho_Chi_Minh",
        startLocalTime = LocalTime.of(9, 0),
        endLocalTime = LocalTime.of(17, 0),
        items = listOf(
            ItineraryDraftItem(
                title = "Bưu điện Trung tâm Sài Gòn",
                startLocalTime = LocalTime.of(9, 0),
                endLocalTime = LocalTime.of(13, 0),
            ),
            ItineraryDraftItem(
                title = "Bảo tàng Chứng tích Chiến tranh",
                startLocalTime = LocalTime.of(13, 0),
                endLocalTime = LocalTime.of(17, 0),
            ),
        ),
        assumptions = listOf("Chưa tính thời gian di chuyển."),
        warnings = listOf(ItineraryDraftWarning("Hãy kiểm tra giờ mở cửa.")),
    )
}
