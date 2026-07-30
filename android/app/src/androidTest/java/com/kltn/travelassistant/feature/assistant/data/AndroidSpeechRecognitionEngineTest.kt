package com.kltn.travelassistant.feature.assistant.data

import android.content.Intent
import android.os.Bundle
import android.speech.RecognizerIntent
import android.speech.SpeechRecognizer
import android.speech.RecognitionListener as AndroidRecognitionListener
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.kltn.travelassistant.feature.assistant.domain.SpeechRecognitionEvent
import com.kltn.travelassistant.feature.assistant.domain.SpeechRecognitionFailure
import com.kltn.travelassistant.feature.assistant.domain.SpeechRecognitionStartResult
import com.kltn.travelassistant.feature.assistant.domain.SpeechRecognitionListener as FeatureSpeechRecognitionListener
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class AndroidSpeechRecognitionEngineTest {
    @Test
    fun availabilityCheckCreatesNoRecognizer() {
        val fixture = EngineFixture()

        assertTrue(fixture.engine.isAvailable())
        assertEquals(1, fixture.availabilityCheckCount)
        assertEquals(0, fixture.factoryCallCount)
    }

    @Test
    fun firstStartCreatesRecognizerLazilyAndSecondActiveStartIsBusy() {
        val fixture = EngineFixture()

        assertEquals(
            SpeechRecognitionStartResult.Started,
            fixture.engine.start("vi-VN", fixture.listener),
        )
        assertEquals(1, fixture.factoryCallCount)
        assertEquals(listOf("setListener", "start"), fixture.platform.operations)

        assertEquals(
            SpeechRecognitionStartResult.Failure(SpeechRecognitionFailure.BUSY),
            fixture.engine.start("vi-VN", fixture.listener),
        )
        assertEquals(1, fixture.factoryCallCount)
    }

    @Test
    fun cancelInvalidatesLateCallbacks() {
        val fixture = EngineFixture()
        fixture.engine.start("vi-VN", fixture.listener)
        val staleListener = requireNotNull(fixture.platform.listener)

        fixture.engine.cancel()
        staleListener.onResults(resultsBundle("late result"))

        assertEquals(
            listOf(SpeechRecognitionEvent.Cancelled),
            fixture.events,
        )
        assertEquals(listOf("setListener", "start", "cancel"), fixture.platform.operations)
    }

    @Test
    fun replacementSessionIgnoresCallbacksFromThePreviousListener() {
        val fixture = EngineFixture()
        fixture.engine.start("vi-VN", fixture.listener)
        val firstPlatformListener = requireNotNull(fixture.platform.listener)
        firstPlatformListener.onResults(resultsBundle("first result"))
        fixture.events.clear()

        fixture.engine.start("vi-VN", fixture.listener)
        firstPlatformListener.onResults(resultsBundle("stale result"))

        assertTrue(fixture.events.isEmpty())
    }

    @Test
    fun closeWhileActiveCancelsThenDestroysAndLateCallbacksAreIgnored() {
        val fixture = EngineFixture()
        fixture.engine.start("vi-VN", fixture.listener)
        val staleListener = requireNotNull(fixture.platform.listener)

        fixture.engine.close()
        staleListener.onResults(resultsBundle("late result"))

        assertEquals(
            listOf("setListener", "start", "cancel", "destroy"),
            fixture.platform.operations,
        )
        assertTrue(fixture.events.isEmpty())
    }

    @Test
    fun closeTwiceDestroysExactlyOnceAndCancelAfterCloseIsSafe() {
        val fixture = EngineFixture()
        fixture.engine.start("vi-VN", fixture.listener)

        fixture.engine.close()
        fixture.engine.close()
        fixture.engine.cancel()

        assertEquals(1, fixture.platform.operations.count { it == "cancel" })
        assertEquals(1, fixture.platform.operations.count { it == "destroy" })
    }

    @Test
    fun startAfterCloseFailsWithoutAvailabilityOrFactoryCall() {
        val fixture = EngineFixture()
        fixture.engine.close()

        val result = fixture.engine.start("vi-VN", fixture.listener)

        assertEquals(
            SpeechRecognitionStartResult.Failure(SpeechRecognitionFailure.CLIENT),
            result,
        )
        assertEquals(0, fixture.availabilityCheckCount)
        assertEquals(0, fixture.factoryCallCount)
    }

    @Test
    fun nonMainThreadOperationsNeverCallSpeechRecognizerPlatform() {
        val fixture = EngineFixture(isMainThread = false)

        assertFalse(fixture.engine.isAvailable())
        assertEquals(
            SpeechRecognitionStartResult.Failure(SpeechRecognitionFailure.CLIENT),
            fixture.engine.start("vi-VN", fixture.listener),
        )
        fixture.engine.cancel()
        fixture.engine.close()

        assertEquals(0, fixture.availabilityCheckCount)
        assertEquals(0, fixture.factoryCallCount)
        assertTrue(fixture.platform.operations.isEmpty())
    }

    @Test
    fun recognitionIntentUsesVietnameseFreeFormAndPartialResults() {
        val intent = createRecognitionIntent("vi-VN")

        assertEquals(RecognizerIntent.ACTION_RECOGNIZE_SPEECH, intent.action)
        assertEquals(
            RecognizerIntent.LANGUAGE_MODEL_FREE_FORM,
            intent.getStringExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL),
        )
        assertEquals("vi-VN", intent.getStringExtra(RecognizerIntent.EXTRA_LANGUAGE))
        assertTrue(intent.getBooleanExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, false))
        assertEquals(1, intent.getIntExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 0))
    }

    @Test
    fun everyCompileSdkSpeechRecognizerErrorMapsToClosedFailureTaxonomy() {
        val expected = mapOf(
            SpeechRecognizer.ERROR_NETWORK_TIMEOUT to SpeechRecognitionFailure.NETWORK,
            SpeechRecognizer.ERROR_NETWORK to SpeechRecognitionFailure.NETWORK,
            SpeechRecognizer.ERROR_AUDIO to SpeechRecognitionFailure.AUDIO,
            SpeechRecognizer.ERROR_SERVER to SpeechRecognitionFailure.SERVICE,
            SpeechRecognizer.ERROR_CLIENT to SpeechRecognitionFailure.CLIENT,
            SpeechRecognizer.ERROR_SPEECH_TIMEOUT to SpeechRecognitionFailure.NO_SPEECH,
            SpeechRecognizer.ERROR_NO_MATCH to SpeechRecognitionFailure.NO_MATCH,
            SpeechRecognizer.ERROR_RECOGNIZER_BUSY to SpeechRecognitionFailure.BUSY,
            SpeechRecognizer.ERROR_INSUFFICIENT_PERMISSIONS to
                SpeechRecognitionFailure.PERMISSION_DENIED,
            SpeechRecognizer.ERROR_TOO_MANY_REQUESTS to SpeechRecognitionFailure.SERVICE,
            SpeechRecognizer.ERROR_SERVER_DISCONNECTED to SpeechRecognitionFailure.SERVICE,
            SpeechRecognizer.ERROR_LANGUAGE_NOT_SUPPORTED to
                SpeechRecognitionFailure.LANGUAGE_UNAVAILABLE,
            SpeechRecognizer.ERROR_LANGUAGE_UNAVAILABLE to
                SpeechRecognitionFailure.LANGUAGE_UNAVAILABLE,
            SpeechRecognizer.ERROR_CANNOT_CHECK_SUPPORT to SpeechRecognitionFailure.SERVICE,
            SpeechRecognizer.ERROR_CANNOT_LISTEN_TO_DOWNLOAD_EVENTS to
                SpeechRecognitionFailure.SERVICE,
        )

        assertEquals(15, expected.size)
        expected.forEach { (platformError, expectedFailure) ->
            assertEquals(expectedFailure, platformError.toSpeechRecognitionFailure())
        }
        assertEquals(
            SpeechRecognitionFailure.SERVICE,
            Int.MAX_VALUE.toSpeechRecognitionFailure(),
        )
    }

    private class EngineFixture(
        private val isMainThread: Boolean = true,
    ) {
        val events = mutableListOf<SpeechRecognitionEvent>()
        val platform = FakeSpeechRecognizerPlatform()
        var availabilityCheckCount = 0
        var factoryCallCount = 0
        val listener = FeatureSpeechRecognitionListener(events::add)
        val engine = AndroidSpeechRecognitionEngine(
            availabilityChecker = {
                availabilityCheckCount += 1
                true
            },
            platformFactory = {
                factoryCallCount += 1
                platform
            },
            mainThreadChecker = { isMainThread },
            intentFactory = { languageTag -> Intent("test.$languageTag") },
        )
    }

    private class FakeSpeechRecognizerPlatform : SpeechRecognizerPlatform {
        val operations = mutableListOf<String>()
        var listener: AndroidRecognitionListener? = null

        override fun setRecognitionListener(listener: AndroidRecognitionListener) {
            operations += "setListener"
            this.listener = listener
        }

        override fun startListening(intent: Intent) {
            operations += "start"
        }

        override fun cancel() {
            operations += "cancel"
        }

        override fun destroy() {
            operations += "destroy"
        }
    }

    private companion object {
        fun resultsBundle(transcript: String): Bundle = Bundle().apply {
            putStringArrayList(
                SpeechRecognizer.RESULTS_RECOGNITION,
                arrayListOf(transcript),
            )
        }
    }
}
