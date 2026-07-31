package com.kltn.travelassistant.feature.assistant

import java.io.File
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class AssistantVoiceInputPolicyTest {
    @Test
    fun applicationVoiceFlowUsesNoGboardOrKeyboardVoiceInputApi() {
        val source = productionAssistantSource()

        assertTrue(source.contains("RecognizerIntent.ACTION_RECOGNIZE_SPEECH"))
        FORBIDDEN_VOICE_INTEGRATIONS.forEach { forbiddenToken ->
            assertFalse(
                "Application speech input must not use $forbiddenToken",
                source.contains(forbiddenToken),
            )
        }
    }

    @Test
    fun speechRecognitionFlowUsesNoRecordingOrPersistenceApi() {
        val source = speechRecognitionSource()

        FORBIDDEN_RECORDING_PERSISTENCE_AND_TRANSPORT.forEach { forbiddenToken ->
            assertFalse(
                "T060 speech source must not use $forbiddenToken",
                source.contains(forbiddenToken),
            )
        }
    }

    @Test
    fun attemptIdentityNeverEntersUiStateOrLogs() {
        val appProjectDirectory = findAppProjectDirectory()
        val uiStateSource = appProjectDirectory
            .resolve(
                "src/main/java/com/kltn/travelassistant/feature/assistant/" +
                    "presentation/AssistantUiState.kt",
            )
            .readText()

        assertFalse(uiStateSource.contains("attempt", ignoreCase = true))
        assertFalse(productionAssistantSource().contains("android.util.Log"))
    }

    @Test
    fun assistantSubmissionHasNoAudioPersistenceWorkManagerOrLogging() {
        val source = productionAssistantSource()
        val requestDocument = source
            .substringAfter("private data class AssistantRequestDocument(")
            .substringBefore(")\n\n@Serializable")

        listOf(
            "audio",
            "file",
            "recording",
            "mimeType",
            "uri",
            "ByteArray",
        ).forEach { forbiddenField ->
            assertFalse(
                "Assistant JSON request must not contain $forbiddenField",
                requestDocument.contains(forbiddenField, ignoreCase = true),
            )
        }
        listOf(
            "WorkManager",
            "RoomDatabase",
            "DataStore<",
            "SharedPreferences",
            "android.util.Log",
        ).forEach { forbiddenDependency ->
            assertFalse(
                "Assistant submission must not use $forbiddenDependency",
                source.contains(forbiddenDependency),
            )
        }
    }

    @Test
    fun mainActivityResumeForwardsPermissionWithoutStartingOrRequestingVoiceInput() {
        val source = mainActivitySource()
        val onResumeBody = source
            .substringAfter("override fun onResume()")
            .substringBefore("override fun onStop()")

        assertTrue(
            onResumeBody.contains(
                "assistantViewModel.onMicrophonePermissionStatusRefreshed(",
            ),
        )
        assertTrue(onResumeBody.contains("isGranted = hasMicrophonePermission()"))
        listOf(
            "beginVoiceInputAttempt",
            "onMicrophonePermissionGranted",
            "microphonePermissionLauncher.launch",
            "start(",
        ).forEach { forbiddenToken ->
            assertFalse(
                "onResume must not invoke $forbiddenToken",
                onResumeBody.contains(forbiddenToken),
            )
        }
    }

    private fun productionAssistantSource(): String {
        val appProjectDirectory = findAppProjectDirectory()
        val sourceRoot = appProjectDirectory.resolve("src/main/java")
        return sourceRoot.walkTopDown()
            .filter(File::isFile)
            .filter { file ->
                file.extension == "kt" &&
                    (
                        "/feature/assistant/" in file.invariantSeparatorsPath ||
                            file.name == "MainActivity.kt"
                    )
            }
            .sortedBy(File::getPath)
            .joinToString(separator = "\n", transform = File::readText)
    }

    private fun mainActivitySource(): String = findAppProjectDirectory()
        .resolve("src/main/java/com/kltn/travelassistant/MainActivity.kt")
        .readText()

    private fun speechRecognitionSource(): String {
        val appProjectDirectory = findAppProjectDirectory()
        val sourceRoot = appProjectDirectory.resolve("src/main/java")
        return sourceRoot.walkTopDown()
            .filter(File::isFile)
            .filter { file ->
                file.extension == "kt" &&
                    (
                        "SpeechRecognition" in file.name ||
                            file.name == "MainActivity.kt"
                    )
            }
            .sortedBy(File::getPath)
            .joinToString(separator = "\n", transform = File::readText)
    }

    private fun findAppProjectDirectory(): File {
        val workingDirectory = File(requireNotNull(System.getProperty("user.dir")))
        return listOf(
            workingDirectory,
            workingDirectory.resolve("app"),
            workingDirectory.resolve("android/app"),
        ).firstOrNull { candidate ->
            candidate.resolve("build.gradle.kts").isFile && candidate.resolve("src").isDirectory
        } ?: error("Unable to locate the Android app module")
    }

    private companion object {
        val FORBIDDEN_VOICE_INTEGRATIONS = listOf(
            "com.google.android.inputmethod",
            "Gboard",
            "ACTION_VOICE_SEARCH_HANDS_FREE",
            "ACTION_WEB_SEARCH",
            "getVoiceDetailsIntent",
            "EXTRA_AUDIO_SOURCE",
            "EXTRA_PREFER_OFFLINE",
            "EXTRA_SPEECH_INPUT_",
            "InputMethodService",
            "createSpeechRecognizer(context,",
        )
        val FORBIDDEN_RECORDING_PERSISTENCE_AND_TRANSPORT = listOf(
            "MediaRecorder",
            "AudioRecord",
            "startRecording",
            "DataStore",
            "SharedPreferences",
            "RoomDatabase",
            "java.io.File",
            "retrofit2",
            "okhttp3",
            "BACKEND_BASE_URL",
        )
    }
}
