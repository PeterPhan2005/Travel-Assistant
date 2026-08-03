package com.kltn.travelassistant.feature.itinerary

import java.io.File
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class ItinerarySourcePolicyTest {
    @Test
    fun productionGeneratorUsesOnlyTheTypedStructuredEndpoint() {
        val source = itinerarySource()

        assertTrue(source.contains("DefaultItineraryDraftGenerator"))
        assertTrue(source.contains("v1/itinerary-drafts/generate"))
        assertFalse(source.contains("class UnsupportedTransportItineraryDraftGenerator"))
        assertFalse(source.contains("AssistantQueryRepository"))
        assertFalse(source.contains("AssistantHttpApi"))
        assertFalse(source.contains("/v1/assistant/query"))
    }

    @Test
    fun t070SourceUsesNoPersistenceBackgroundAnalyticsAudioOrLoggingApi() {
        val source = itinerarySource()
        listOf(
            "ItineraryDao",
            "RoomDatabase",
            "DataStore",
            "SharedPreferences",
            "WorkManager",
            "SavedStateHandle",
            "MediaRecorder",
            "AudioRecord",
            "android.util.Log",
            "FirebaseAnalytics",
            "/itineraries",
        ).forEach { forbiddenToken ->
            assertFalse(
                "T070 production source must not use $forbiddenToken",
                source.contains(forbiddenToken),
            )
        }
    }

    @Test
    fun uiAndDomainModelsExposeNoTransportOrInternalAgentDetails() {
        val source = itineraryModelSource()
        listOf(
            "okhttp3",
            "kotlinx.serialization",
            "HttpUrl",
            "requestId",
            "traceId",
            "claimId",
            "sourceId",
            "agentName",
            "stageName",
            "Throwable",
        ).forEach { forbiddenToken ->
            assertFalse(
                "T070 public feature models must not expose $forbiddenToken",
                source.contains(forbiddenToken),
            )
        }
    }

    private fun itinerarySource(): String {
        val appProjectDirectory = findAppProjectDirectory()
        return appProjectDirectory
            .resolve("src/main/java/com/kltn/travelassistant/feature/itinerary")
            .walkTopDown()
            .filter(File::isFile)
            .filter { it.extension == "kt" }
            .sortedBy(File::getPath)
            .joinToString(separator = "\n", transform = File::readText)
    }

    private fun itineraryModelSource(): String {
        val featureDirectory = findAppProjectDirectory()
            .resolve("src/main/java/com/kltn/travelassistant/feature/itinerary")
        return listOf(
            featureDirectory.resolve("domain/ItineraryDraftModels.kt"),
            featureDirectory.resolve("domain/ItineraryDraftGenerator.kt"),
            featureDirectory.resolve("domain/ItinerarySaveBoundary.kt"),
            featureDirectory.resolve("presentation/ItineraryUiState.kt"),
        ).joinToString(separator = "\n", transform = File::readText)
    }

    private fun findAppProjectDirectory(): File {
        val workingDirectory = File(requireNotNull(System.getProperty("user.dir")))
        return listOf(
            workingDirectory,
            workingDirectory.resolve("app"),
            workingDirectory.resolve("android/app"),
        ).firstOrNull { candidate ->
            candidate.resolve("build.gradle.kts").isFile &&
                candidate.resolve("src").isDirectory
        } ?: error("Unable to locate the Android app module")
    }
}
