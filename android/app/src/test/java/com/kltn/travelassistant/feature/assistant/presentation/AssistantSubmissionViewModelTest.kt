package com.kltn.travelassistant.feature.assistant.presentation

import com.kltn.travelassistant.feature.assistant.domain.AssistantIntent
import com.kltn.travelassistant.feature.assistant.domain.AssistantIntentAnalytics
import com.kltn.travelassistant.feature.assistant.domain.AssistantIntentOutcome
import com.kltn.travelassistant.feature.assistant.domain.AssistantLocationSnapshot
import com.kltn.travelassistant.feature.assistant.domain.AssistantQueryFailure
import com.kltn.travelassistant.feature.assistant.domain.AssistantQueryRepository
import com.kltn.travelassistant.feature.assistant.domain.AssistantQueryRequest
import com.kltn.travelassistant.feature.assistant.domain.AssistantQueryResult
import com.kltn.travelassistant.feature.assistant.domain.AssistantRepositoryResult
import com.kltn.travelassistant.feature.assistant.domain.AssistantResultStatus
import com.kltn.travelassistant.feature.assistant.domain.SpeechRecognitionEngine
import com.kltn.travelassistant.feature.assistant.domain.SpeechRecognitionListener
import com.kltn.travelassistant.feature.assistant.domain.SpeechRecognitionStartResult
import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.NonCancellable
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.advanceUntilIdle
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.test.setMain
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.withContext
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test

@OptIn(ExperimentalCoroutinesApi::class)
class AssistantSubmissionViewModelTest {
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
    fun blankIsIgnoredAndOver500IsRejectedWithoutRepositoryCall() {
        val repository = FakeRepository()
        val viewModel = viewModel(repository)

        viewModel.onQueryChanged("   ")
        viewModel.submitQuery(isOnline = true, location = null)
        assertEquals(AssistantSubmissionUiState.Idle, viewModel.uiState.value.querySubmissionState)

        viewModel.onQueryChanged("a".repeat(501))
        viewModel.submitQuery(isOnline = true, location = null)

        assertEquals(
            AssistantSubmissionUiState.QueryTooLong,
            viewModel.uiState.value.querySubmissionState,
        )
        assertTrue(repository.requests.isEmpty())
    }

    @Test
    fun latestEditedTextAndOptionalLocationBecomeOneImmutableSnapshot() = runTest {
        val repository = FakeRepository(result = structured())
        val viewModel = viewModel(repository)
        viewModel.onQueryChanged("kết quả nhận dạng cũ")
        viewModel.onQueryChanged("  Tôi muốn ăn phở đã sửa  ")
        val location = AssistantLocationSnapshot(10.776, 106.7)

        viewModel.submitQuery(isOnline = true, location = location)
        advanceUntilIdle()

        assertEquals(
            listOf(
                AssistantQueryRequest(
                    text = "Tôi muốn ăn phở đã sửa",
                    location = location,
                ),
            ),
            repository.requests,
        )
        assertEquals("Tôi muốn ăn phở đã sửa", viewModel.uiState.value.queryText)
        assertEquals(
            "Tôi muốn ăn phở đã sửa",
            viewModel.uiState.value.confirmedTranscript,
        )
    }

    @Test
    fun loadingIgnoresDuplicateAndExplicitCancellationRetainsText() = runTest {
        val gate = CompletableDeferred<AssistantRepositoryResult>()
        val repository = FakeRepository(gate = gate)
        val viewModel = viewModel(repository)
        viewModel.onQueryChanged("Câu hỏi giữ lại")

        viewModel.submitQuery(isOnline = true, location = null)
        dispatcher.scheduler.runCurrent()
        assertEquals(
            AssistantSubmissionUiState.Loading,
            viewModel.uiState.value.querySubmissionState,
        )
        viewModel.submitQuery(isOnline = true, location = null)
        assertEquals(1, repository.requests.size)

        viewModel.cancelQuery()

        assertEquals(
            AssistantSubmissionUiState.Cancelled,
            viewModel.uiState.value.querySubmissionState,
        )
        assertEquals("Câu hỏi giữ lại", viewModel.uiState.value.queryText)
    }

    @Test
    fun successPartialAndFailedRecordOnlyIntentOutcomeOnce() = runTest {
        for (status in AssistantResultStatus.entries) {
            val analytics = RecordingAnalytics()
            val repository = FakeRepository(
                result = structured(status = status),
            )
            val viewModel = viewModel(repository, analytics)
            viewModel.onQueryChanged("Câu hỏi")

            viewModel.submitQuery(isOnline = true, location = null)
            advanceUntilIdle()

            assertEquals(
                listOf(
                    AssistantIntent.GENERAL_TRAVEL_HELP to when (status) {
                        AssistantResultStatus.SUCCESS -> AssistantIntentOutcome.SUCCESS
                        AssistantResultStatus.PARTIAL -> AssistantIntentOutcome.PARTIAL
                        AssistantResultStatus.FAILED -> AssistantIntentOutcome.FAILED
                    },
                ),
                analytics.events,
            )
            assertTrue(viewModel.uiState.value.querySubmissionState !is AssistantSubmissionUiState.Error)
        }
    }

    @Test
    fun offlineAuthAndTransportFailuresNeverRecordFabricatedIntent() = runTest {
        val analytics = RecordingAnalytics()
        val repository = FakeRepository(
            result = AssistantRepositoryResult.Failure(
                AssistantQueryFailure.AUTHENTICATION_REQUIRED,
            ),
        )
        val viewModel = viewModel(repository, analytics)
        viewModel.onQueryChanged("Câu hỏi riêng")

        viewModel.submitQuery(isOnline = false, location = null)
        assertEquals(
            AssistantSubmissionUiState.Offline,
            viewModel.uiState.value.querySubmissionState,
        )
        assertTrue(repository.requests.isEmpty())

        viewModel.submitQuery(isOnline = true, location = null)
        advanceUntilIdle()
        assertEquals(
            AssistantSubmissionUiState.AuthenticationRequired,
            viewModel.uiState.value.querySubmissionState,
        )
        assertEquals("Câu hỏi riêng", viewModel.uiState.value.queryText)
        assertTrue(analytics.events.isEmpty())
    }

    @Test
    fun retryIsExplicitAndUsesSameSnapshotUntilEdit() = runTest {
        val repository = QueueRepository(
            mutableListOf(
                AssistantRepositoryResult.Failure(AssistantQueryFailure.TIMEOUT),
                structured(),
            ),
        )
        val viewModel = viewModel(repository)
        val location = AssistantLocationSnapshot(10.7, 106.6)
        viewModel.onQueryChanged("  Câu hỏi thử lại  ")

        viewModel.submitQuery(isOnline = true, location = location)
        advanceUntilIdle()
        assertEquals(1, repository.requests.size)
        assertTrue(viewModel.uiState.value.querySubmissionState is AssistantSubmissionUiState.Error)

        advanceUntilIdle()
        assertEquals(1, repository.requests.size)
        viewModel.retryQuery(isOnline = true)
        advanceUntilIdle()

        assertEquals(2, repository.requests.size)
        assertEquals(repository.requests[0], repository.requests[1])
    }

    @Test
    fun editCancelsRequestClearsStaleResultAndLateCompletionIsIgnored() = runTest {
        val gate = CompletableDeferred<AssistantRepositoryResult>()
        val repository = FakeRepository(gate = gate, ignoreCancellation = true)
        val viewModel = viewModel(repository)
        viewModel.onQueryChanged("Câu hỏi cũ")
        viewModel.submitQuery(isOnline = true, location = null)
        dispatcher.scheduler.runCurrent()

        viewModel.onQueryChanged("Câu hỏi mới")
        gate.complete(structured())
        advanceUntilIdle()

        assertEquals("Câu hỏi mới", viewModel.uiState.value.queryText)
        assertNull(viewModel.uiState.value.confirmedTranscript)
        assertEquals(
            AssistantSubmissionUiState.Idle,
            viewModel.uiState.value.querySubmissionState,
        )
    }

    @Test
    fun screenDepartureAndBackgroundCancelWithoutAutoRestart() = runTest {
        val gate = CompletableDeferred<AssistantRepositoryResult>()
        val repository = FakeRepository(gate = gate)
        val viewModel = viewModel(repository)
        viewModel.onQueryChanged("Câu hỏi")
        viewModel.submitQuery(isOnline = true, location = null)
        dispatcher.scheduler.runCurrent()

        viewModel.onAssistantScreenLeft()

        assertEquals(
            AssistantSubmissionUiState.Cancelled,
            viewModel.uiState.value.querySubmissionState,
        )
        assertEquals(1, repository.requests.size)
        dispatcher.scheduler.runCurrent()
        assertEquals(1, repository.requests.size)

        viewModel.submitQuery(isOnline = true, location = null)
        dispatcher.scheduler.runCurrent()
        viewModel.onAppBackgrounded()
        assertEquals(
            AssistantSubmissionUiState.Cancelled,
            viewModel.uiState.value.querySubmissionState,
        )
    }

    private fun viewModel(
        repository: AssistantQueryRepository,
        analytics: AssistantIntentAnalytics = RecordingAnalytics(),
    ) = AssistantViewModel(
        speechRecognitionEngine = FakeSpeechEngine(),
        queryRepository = repository,
        intentAnalytics = analytics,
    )

    private class FakeRepository(
        private val result: AssistantRepositoryResult? = null,
        private val gate: CompletableDeferred<AssistantRepositoryResult>? = null,
        private val ignoreCancellation: Boolean = false,
    ) : AssistantQueryRepository {
        val requests = mutableListOf<AssistantQueryRequest>()

        override suspend fun submit(
            request: AssistantQueryRequest,
        ): AssistantRepositoryResult {
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

    private class QueueRepository(
        private val results: MutableList<AssistantRepositoryResult>,
    ) : AssistantQueryRepository {
        val requests = mutableListOf<AssistantQueryRequest>()

        override suspend fun submit(
            request: AssistantQueryRequest,
        ): AssistantRepositoryResult {
            requests += request
            return results.removeAt(0)
        }
    }

    private class RecordingAnalytics : AssistantIntentAnalytics {
        val events = mutableListOf<Pair<AssistantIntent, AssistantIntentOutcome>>()

        override fun record(
            intent: AssistantIntent,
            outcome: AssistantIntentOutcome,
        ) {
            events += intent to outcome
        }
    }

    private class FakeSpeechEngine : SpeechRecognitionEngine {
        override fun isAvailable() = true

        override fun start(
            languageTag: String,
            listener: SpeechRecognitionListener,
        ) = SpeechRecognitionStartResult.Started

        override fun cancel() = Unit

        override fun close() = Unit
    }

    private fun structured(
        status: AssistantResultStatus = AssistantResultStatus.SUCCESS,
    ) = AssistantRepositoryResult.Structured(
        AssistantQueryResult(
            status = status,
            intent = AssistantIntent.GENERAL_TRAVEL_HELP,
            message = if (status == AssistantResultStatus.FAILED) {
                "Chưa thể tạo câu trả lời an toàn."
            } else {
                "Câu trả lời"
            },
            poiResults = emptyList(),
            narration = null,
            itinerary = null,
            sources = emptyList(),
            warnings = emptyList(),
            retryable = false,
        ),
    )
}
