package com.kltn.travelassistant.feature.assistant.presentation

import com.kltn.travelassistant.feature.assistant.domain.SpeechRecognitionEngine
import com.kltn.travelassistant.feature.assistant.domain.SpeechRecognitionEvent
import com.kltn.travelassistant.feature.assistant.domain.SpeechRecognitionFailure
import com.kltn.travelassistant.feature.assistant.domain.SpeechRecognitionListener
import com.kltn.travelassistant.feature.assistant.domain.SpeechRecognitionStartResult
import com.kltn.travelassistant.feature.assistant.domain.MAX_ASSISTANT_QUERY_CODE_POINTS
import com.kltn.travelassistant.feature.assistant.domain.normalizeConfirmedAssistantQuery
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class AssistantViewModelTest {
    @Test
    fun initialStateChecksAvailabilityWithoutStartingOrRequestingAnything() {
        val engine = FakeSpeechRecognitionEngine()
        val viewModel = AssistantViewModel(engine)

        assertEquals(AssistantUiState(), viewModel.uiState.value)
        assertEquals(1, engine.availabilityCheckCount)
        assertEquals(0, engine.startCount)
        assertEquals(0, engine.cancelCount)
    }

    @Test
    fun unavailableServiceKeepsManualComposerUsable() {
        val engine = FakeSpeechRecognitionEngine(available = false)
        val viewModel = AssistantViewModel(engine)

        assertEquals(SpeechInputUiState.Unavailable, viewModel.uiState.value.speechInputState)

        viewModel.onQueryChanged("Đi chợ nào gần đây?")
        viewModel.confirmTranscript()

        assertEquals("Đi chợ nào gần đây?", viewModel.uiState.value.queryText)
        assertEquals("Đi chợ nào gần đây?", viewModel.uiState.value.confirmedTranscript)
        assertEquals(SpeechInputUiState.Unavailable, viewModel.uiState.value.speechInputState)
        assertEquals(0, engine.startCount)
    }

    @Test
    fun manualTextCanBeEditedConfirmedLocallyAndEditedAgain() {
        val viewModel = AssistantViewModel(FakeSpeechRecognitionEngine())

        viewModel.onQueryChanged("  Tôi muốn ăn phở  ")
        assertNull(viewModel.uiState.value.confirmedTranscript)

        viewModel.confirmTranscript()
        assertEquals("Tôi muốn ăn phở", viewModel.uiState.value.queryText)
        assertEquals("Tôi muốn ăn phở", viewModel.uiState.value.confirmedTranscript)

        viewModel.onQueryChanged("Tôi muốn ăn bún bò")
        assertEquals("Tôi muốn ăn bún bò", viewModel.uiState.value.queryText)
        assertNull(viewModel.uiState.value.confirmedTranscript)
    }

    @Test
    fun permissionRequestAndDenialDoNotStartRecognition() {
        val engine = FakeSpeechRecognitionEngine()
        val viewModel = AssistantViewModel(engine)
        val attemptId = requireNotNull(viewModel.beginVoiceInputAttempt())

        viewModel.onMicrophonePermissionRequestStarted(attemptId)
        assertEquals(
            SpeechInputUiState.PermissionRequesting,
            viewModel.uiState.value.speechInputState,
        )
        assertEquals(0, engine.startCount)

        viewModel.onMicrophonePermissionDenied(
            attemptId = attemptId,
            canRequestPermissionAgain = false,
        )
        assertEquals(
            SpeechInputUiState.PermissionDenied(canRequestPermissionAgain = false),
            viewModel.uiState.value.speechInputState,
        )
        assertEquals(0, engine.startCount)
    }

    @Test
    fun grantedPermissionRefreshClearsDenialAndPreservesTextAndConfirmation() {
        val engine = FakeSpeechRecognitionEngine()
        val viewModel = AssistantViewModel(engine)
        viewModel.onQueryChanged("  Nội dung đã xác nhận  ")
        viewModel.confirmTranscript()
        val attemptId = requireNotNull(viewModel.beginVoiceInputAttempt())
        viewModel.onMicrophonePermissionDenied(
            attemptId = attemptId,
            canRequestPermissionAgain = false,
        )

        viewModel.onMicrophonePermissionStatusRefreshed(isGranted = true)

        assertEquals(SpeechInputUiState.Idle, viewModel.uiState.value.speechInputState)
        assertEquals("Nội dung đã xác nhận", viewModel.uiState.value.queryText)
        assertEquals("Nội dung đã xác nhận", viewModel.uiState.value.confirmedTranscript)
        assertEquals(0, engine.startCount)
        assertEquals(0, engine.cancelCount)
        assertEquals(2L, viewModel.beginVoiceInputAttempt())
    }

    @Test
    fun deniedPermissionRefreshPreservesPermissionDeniedWithoutEngineCalls() {
        val engine = FakeSpeechRecognitionEngine()
        val viewModel = AssistantViewModel(engine)
        val attemptId = requireNotNull(viewModel.beginVoiceInputAttempt())
        viewModel.onMicrophonePermissionDenied(
            attemptId = attemptId,
            canRequestPermissionAgain = false,
        )
        val expectedState = viewModel.uiState.value

        viewModel.onMicrophonePermissionStatusRefreshed(isGranted = false)

        assertEquals(expectedState, viewModel.uiState.value)
        assertEquals(0, engine.startCount)
        assertEquals(0, engine.cancelCount)
        assertEquals(2L, viewModel.beginVoiceInputAttempt())
    }

    @Test
    fun permissionRefreshWhileIdleIsNoOpAndCreatesNoVoiceAttempt() {
        val engine = FakeSpeechRecognitionEngine()
        val viewModel = AssistantViewModel(engine)
        val expectedState = viewModel.uiState.value

        viewModel.onMicrophonePermissionStatusRefreshed(isGranted = true)

        assertEquals(expectedState, viewModel.uiState.value)
        assertEquals(0, engine.startCount)
        assertEquals(0, engine.cancelCount)
        assertEquals(1L, viewModel.beginVoiceInputAttempt())
    }

    @Test
    fun permissionRefreshWhileCompletedIsNoOpAndDoesNotRestartRecognition() {
        val engine = FakeSpeechRecognitionEngine()
        val viewModel = AssistantViewModel(engine)
        startRecognition(viewModel)
        engine.emit(SpeechRecognitionEvent.FinalTranscript("Tôi muốn ăn phở"))
        val expectedState = viewModel.uiState.value

        viewModel.onMicrophonePermissionStatusRefreshed(isGranted = true)

        assertEquals(expectedState, viewModel.uiState.value)
        assertEquals(1, engine.startCount)
        assertEquals(0, engine.cancelCount)
    }

    @Test
    fun grantedPermissionStartsVietnameseRecognitionAndShowsPartialAndFinalTranscript() {
        val engine = FakeSpeechRecognitionEngine()
        val viewModel = AssistantViewModel(engine)

        startRecognition(viewModel)

        assertEquals(1, engine.startCount)
        assertEquals("vi-VN", engine.languageTag)
        assertEquals(SpeechInputUiState.Starting, viewModel.uiState.value.speechInputState)

        engine.emit(SpeechRecognitionEvent.Ready)
        assertEquals(SpeechInputUiState.Ready, viewModel.uiState.value.speechInputState)

        engine.emit(SpeechRecognitionEvent.Listening)
        assertEquals(
            SpeechInputUiState.Listening(hasPartialTranscript = false),
            viewModel.uiState.value.speechInputState,
        )

        engine.emit(SpeechRecognitionEvent.PartialTranscript("tôi muốn ăn"))
        assertEquals("tôi muốn ăn", viewModel.uiState.value.queryText)
        assertEquals(
            SpeechInputUiState.Listening(hasPartialTranscript = true),
            viewModel.uiState.value.speechInputState,
        )

        engine.emit(SpeechRecognitionEvent.EndOfSpeech)
        assertEquals(SpeechInputUiState.Processing, viewModel.uiState.value.speechInputState)

        engine.emit(SpeechRecognitionEvent.FinalTranscript("Tôi muốn ăn phở gần đây"))
        assertEquals("Tôi muốn ăn phở gần đây", viewModel.uiState.value.queryText)
        assertEquals(SpeechInputUiState.Completed, viewModel.uiState.value.speechInputState)
        assertNull(viewModel.uiState.value.confirmedTranscript)

        viewModel.onQueryChanged("Tôi muốn ăn phở chay gần đây")
        assertEquals("Tôi muốn ăn phở chay gần đây", viewModel.uiState.value.queryText)
        assertEquals(SpeechInputUiState.Idle, viewModel.uiState.value.speechInputState)
    }

    @Test
    fun explicitCancellationStopsEngineAndIgnoresLateTranscript() {
        val engine = FakeSpeechRecognitionEngine()
        val viewModel = AssistantViewModel(engine)
        viewModel.onQueryChanged("Nội dung trước đó")
        startRecognition(viewModel)
        engine.emit(SpeechRecognitionEvent.PartialTranscript("bản ghi tạm"))

        viewModel.cancelSpeechRecognition()

        assertEquals(1, engine.cancelCount)
        assertEquals(SpeechInputUiState.Cancelled, viewModel.uiState.value.speechInputState)
        assertEquals("bản ghi tạm", viewModel.uiState.value.queryText)

        engine.emit(SpeechRecognitionEvent.FinalTranscript("kết quả đến muộn"))
        assertEquals("bản ghi tạm", viewModel.uiState.value.queryText)
        assertEquals(SpeechInputUiState.Cancelled, viewModel.uiState.value.speechInputState)
    }

    @Test
    fun editingDuringRecognitionCancelsBeforeApplyingManualText() {
        val engine = FakeSpeechRecognitionEngine()
        val viewModel = AssistantViewModel(engine)
        startRecognition(viewModel)
        engine.emit(SpeechRecognitionEvent.Listening)

        viewModel.onQueryChanged("Nội dung tôi tự sửa")

        assertEquals(1, engine.cancelCount)
        assertEquals("Nội dung tôi tự sửa", viewModel.uiState.value.queryText)
        assertEquals(SpeechInputUiState.Idle, viewModel.uiState.value.speechInputState)
    }

    @Test
    fun noSpeechRetainsEditableTextAndExplicitRetryStartsANewSession() {
        val engine = FakeSpeechRecognitionEngine()
        val viewModel = AssistantViewModel(engine)
        viewModel.onQueryChanged("Tôi muốn tìm quán phở gần đây")
        startRecognition(viewModel)

        engine.emit(SpeechRecognitionEvent.Failure(SpeechRecognitionFailure.NO_SPEECH))

        assertEquals(
            "Tôi muốn tìm quán phở gần đây",
            viewModel.uiState.value.queryText,
        )
        assertEquals(
            SpeechInputUiState.Error(SpeechRecognitionFailure.NO_SPEECH),
            viewModel.uiState.value.speechInputState,
        )

        startRecognition(viewModel)

        assertEquals(2, engine.startCount)
        assertEquals(SpeechInputUiState.Starting, viewModel.uiState.value.speechInputState)
    }

    @Test
    fun typedRecognitionFailuresNeverExposePlatformCodesOrExceptions() {
        val engine = FakeSpeechRecognitionEngine()
        val viewModel = AssistantViewModel(engine)

        val recoverableFailures = SpeechRecognitionFailure.entries - setOf(
            SpeechRecognitionFailure.SERVICE_UNAVAILABLE,
            SpeechRecognitionFailure.PERMISSION_DENIED,
        )
        recoverableFailures.forEach { failure ->
            startRecognition(viewModel)
            engine.emit(SpeechRecognitionEvent.Failure(failure))
            assertEquals(
                SpeechInputUiState.Error(failure),
                viewModel.uiState.value.speechInputState,
            )
        }

        startRecognition(viewModel)
        engine.emit(
            SpeechRecognitionEvent.Failure(SpeechRecognitionFailure.PERMISSION_DENIED),
        )
        assertEquals(
            SpeechInputUiState.PermissionDenied(canRequestPermissionAgain = true),
            viewModel.uiState.value.speechInputState,
        )

        startRecognition(viewModel)
        engine.emit(
            SpeechRecognitionEvent.Failure(SpeechRecognitionFailure.SERVICE_UNAVAILABLE),
        )
        assertEquals(SpeechInputUiState.Unavailable, viewModel.uiState.value.speechInputState)
    }

    @Test
    fun synchronousStartFailureBecomesTypedUiState() {
        val engine = FakeSpeechRecognitionEngine(
            startResult = SpeechRecognitionStartResult.Failure(
                SpeechRecognitionFailure.BUSY,
            ),
        )
        val viewModel = AssistantViewModel(engine)

        startRecognition(viewModel)

        assertEquals(
            SpeechInputUiState.Error(SpeechRecognitionFailure.BUSY),
            viewModel.uiState.value.speechInputState,
        )
    }

    @Test
    fun oneVoiceTapCreatesOneAttemptAndDuplicateTapWhilePermissionPendingIsIgnored() {
        val viewModel = AssistantViewModel(FakeSpeechRecognitionEngine())

        val attemptId = viewModel.beginVoiceInputAttempt()
        viewModel.onMicrophonePermissionRequestStarted(requireNotNull(attemptId))

        assertEquals(1L, attemptId)
        assertNull(viewModel.beginVoiceInputAttempt())
        assertEquals(
            SpeechInputUiState.PermissionRequesting,
            viewModel.uiState.value.speechInputState,
        )
    }

    @Test
    fun validGrantStartsExactlyOnceAndDuplicateGrantIsIgnored() {
        val engine = FakeSpeechRecognitionEngine()
        val viewModel = AssistantViewModel(engine)
        val attemptId = requireNotNull(viewModel.beginVoiceInputAttempt())
        viewModel.onMicrophonePermissionRequestStarted(attemptId)

        viewModel.onMicrophonePermissionGranted(attemptId)
        viewModel.onMicrophonePermissionGranted(attemptId)

        assertEquals(1, engine.startCount)
    }

    @Test
    fun staleGrantAndDenialAfterCancelAreIgnored() {
        val engine = FakeSpeechRecognitionEngine()
        val viewModel = AssistantViewModel(engine)
        val attemptId = requireNotNull(viewModel.beginVoiceInputAttempt())
        viewModel.onMicrophonePermissionRequestStarted(attemptId)

        viewModel.cancelSpeechRecognition()
        viewModel.onMicrophonePermissionGranted(attemptId)
        viewModel.onMicrophonePermissionDenied(
            attemptId = attemptId,
            canRequestPermissionAgain = false,
        )

        assertEquals(0, engine.startCount)
        assertEquals(SpeechInputUiState.Cancelled, viewModel.uiState.value.speechInputState)
    }

    @Test
    fun staleGrantAfterScreenLeftIsIgnored() {
        val engine = FakeSpeechRecognitionEngine()
        val viewModel = AssistantViewModel(engine)
        val attemptId = requireNotNull(viewModel.beginVoiceInputAttempt())
        viewModel.onMicrophonePermissionRequestStarted(attemptId)

        viewModel.onAssistantScreenLeft()
        viewModel.onMicrophonePermissionGranted(attemptId)

        assertEquals(0, engine.startCount)
        assertEquals(SpeechInputUiState.Cancelled, viewModel.uiState.value.speechInputState)
    }

    @Test
    fun resultFromAttemptOneCannotStartAttemptTwo() {
        val engine = FakeSpeechRecognitionEngine()
        val viewModel = AssistantViewModel(engine)
        val firstAttempt = requireNotNull(viewModel.beginVoiceInputAttempt())
        viewModel.onMicrophonePermissionRequestStarted(firstAttempt)
        viewModel.cancelSpeechRecognition()
        val secondAttempt = requireNotNull(viewModel.beginVoiceInputAttempt())
        viewModel.onMicrophonePermissionRequestStarted(secondAttempt)

        viewModel.onMicrophonePermissionGranted(firstAttempt)
        assertEquals(0, engine.startCount)

        viewModel.onMicrophonePermissionGranted(secondAttempt)
        assertEquals(1, engine.startCount)
    }

    @Test
    fun hostStopInvalidatesPendingAttempt() {
        val engine = FakeSpeechRecognitionEngine()
        val viewModel = AssistantViewModel(engine)
        val attemptId = requireNotNull(viewModel.beginVoiceInputAttempt())
        viewModel.onMicrophonePermissionRequestStarted(attemptId)

        viewModel.onAssistantScreenLeft()
        viewModel.onMicrophonePermissionGranted(attemptId)

        assertEquals(0, engine.startCount)
        assertEquals(SpeechInputUiState.Cancelled, viewModel.uiState.value.speechInputState)
    }

    @Test
    fun screenLeftCancelsActiveRecognitionRetainsPartialTextAndReturnDoesNotRestart() {
        val engine = FakeSpeechRecognitionEngine()
        val viewModel = AssistantViewModel(engine)
        startRecognition(viewModel)
        engine.emit(SpeechRecognitionEvent.PartialTranscript("  bản ghi tạm  "))

        viewModel.onAssistantScreenLeft()

        assertEquals(1, engine.cancelCount)
        assertEquals("bản ghi tạm", viewModel.uiState.value.queryText)
        assertEquals(SpeechInputUiState.Cancelled, viewModel.uiState.value.speechInputState)

        viewModel.onAssistantScreenLeft()
        assertEquals(1, engine.startCount)
        assertEquals(1, engine.cancelCount)
    }

    @Test
    fun screenLeftDuringPermissionKeepsManualAndConfirmedText() {
        val viewModel = AssistantViewModel(FakeSpeechRecognitionEngine())
        viewModel.onQueryChanged("  Nội dung thủ công  ")
        viewModel.confirmTranscript()
        val attemptId = requireNotNull(viewModel.beginVoiceInputAttempt())
        viewModel.onMicrophonePermissionRequestStarted(attemptId)

        viewModel.onAssistantScreenLeft()

        assertEquals("Nội dung thủ công", viewModel.uiState.value.queryText)
        assertEquals("Nội dung thủ công", viewModel.uiState.value.confirmedTranscript)
        assertEquals(SpeechInputUiState.Cancelled, viewModel.uiState.value.speechInputState)
    }

    @Test
    fun attemptIdentityRolloverIsBoundedAndNeverOverflows() {
        val generator = VoiceInputAttemptIdGenerator(maximumId = 2L)

        assertEquals(1L, generator.next())
        assertEquals(2L, generator.next())
        assertEquals(1L, generator.next())
    }

    @Test
    fun manualTextAtMaximumIsPreservedWithoutTrimming() {
        val viewModel = AssistantViewModel(FakeSpeechRecognitionEngine())
        val text = " " + "ă".repeat(MAX_ASSISTANT_QUERY_CODE_POINTS - 1)

        viewModel.onQueryChanged(text)

        assertEquals(text, viewModel.uiState.value.queryText)
    }

    @Test
    fun manualTextBeyondMaximumIsBoundedByUnicodeCodePoint() {
        val viewModel = AssistantViewModel(FakeSpeechRecognitionEngine())
        val text = "a".repeat(MAX_ASSISTANT_QUERY_CODE_POINTS + 1)

        viewModel.onQueryChanged(text)

        assertEquals(
            "a".repeat(MAX_ASSISTANT_QUERY_CODE_POINTS),
            viewModel.uiState.value.queryText,
        )
    }

    @Test
    fun partialAndFinalTranscriptsAreTrimmedAndBounded() {
        val engine = FakeSpeechRecognitionEngine()
        val viewModel = AssistantViewModel(engine)
        startRecognition(viewModel)
        engine.emit(
            SpeechRecognitionEvent.PartialTranscript(
                "  " + "ộ".repeat(MAX_ASSISTANT_QUERY_CODE_POINTS + 10) + "  ",
            ),
        )
        assertEquals(
            "ộ".repeat(MAX_ASSISTANT_QUERY_CODE_POINTS),
            viewModel.uiState.value.queryText,
        )

        engine.emit(
            SpeechRecognitionEvent.FinalTranscript(
                "  " + "đ".repeat(MAX_ASSISTANT_QUERY_CODE_POINTS + 10) + "  ",
            ),
        )
        assertEquals(
            "đ".repeat(MAX_ASSISTANT_QUERY_CODE_POINTS),
            viewModel.uiState.value.queryText,
        )
    }

    @Test
    fun confirmationTrimsEditedTextAndIgnoresBlankText() {
        val viewModel = AssistantViewModel(FakeSpeechRecognitionEngine())
        viewModel.onQueryChanged("  Nội dung xác nhận  ")

        viewModel.confirmTranscript()

        assertEquals("Nội dung xác nhận", viewModel.uiState.value.confirmedTranscript)

        viewModel.onQueryChanged("   ")
        viewModel.confirmTranscript()
        assertNull(viewModel.uiState.value.confirmedTranscript)
        assertEquals("   ", viewModel.uiState.value.queryText)
    }

    @Test
    fun confirmationBeyondMaximumUsesTheCommonBound() {
        val confirmed = normalizeConfirmedAssistantQuery(
            "  " + "T".repeat(MAX_ASSISTANT_QUERY_CODE_POINTS + 10) + "  ",
        )

        assertEquals("T".repeat(MAX_ASSISTANT_QUERY_CODE_POINTS), confirmed)
    }

    @Test
    fun vietnameseUnicodeAndSurrogatePairsArePreservedWithoutSplitting() {
        val viewModel = AssistantViewModel(FakeSpeechRecognitionEngine())
        val vietnamese = "Tôi muốn tìm quán phở gần đây"
        viewModel.onQueryChanged(vietnamese)
        assertEquals(vietnamese, viewModel.uiState.value.queryText)

        val emoji = "\uD83D\uDE00"
        viewModel.onQueryChanged(
            "a".repeat(MAX_ASSISTANT_QUERY_CODE_POINTS - 1) + emoji + "b",
        )
        val bounded = viewModel.uiState.value.queryText

        assertEquals(MAX_ASSISTANT_QUERY_CODE_POINTS, bounded.codePointCount(0, bounded.length))
        assertEquals(
            "a".repeat(MAX_ASSISTANT_QUERY_CODE_POINTS - 1) + emoji,
            bounded,
        )
    }

    private fun startRecognition(viewModel: AssistantViewModel): Long {
        val attemptId = requireNotNull(viewModel.beginVoiceInputAttempt())
        viewModel.onMicrophonePermissionGranted(attemptId)
        return attemptId
    }

    private class FakeSpeechRecognitionEngine(
        private val available: Boolean = true,
        private val startResult: SpeechRecognitionStartResult =
            SpeechRecognitionStartResult.Started,
    ) : SpeechRecognitionEngine {
        var availabilityCheckCount = 0
        var startCount = 0
        var cancelCount = 0
        var languageTag: String? = null
        private var listener: SpeechRecognitionListener? = null

        override fun isAvailable(): Boolean {
            availabilityCheckCount += 1
            return available
        }

        override fun start(
            languageTag: String,
            listener: SpeechRecognitionListener,
        ): SpeechRecognitionStartResult {
            startCount += 1
            this.languageTag = languageTag
            this.listener = listener
            return startResult
        }

        override fun cancel() {
            cancelCount += 1
        }

        override fun close() = Unit

        fun emit(event: SpeechRecognitionEvent) {
            listener?.onEvent(event)
        }
    }
}
