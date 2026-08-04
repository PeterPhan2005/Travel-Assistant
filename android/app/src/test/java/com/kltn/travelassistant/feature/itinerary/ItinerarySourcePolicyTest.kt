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
        val source = t070Source()
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
    fun t071PersistenceAddsNoSensitiveStorageSearchAnalyticsAudioOrGenerationExecution() {
        val appProjectDirectory = findAppProjectDirectory()
        val entitySource = appProjectDirectory
            .resolve("src/main/java/com/kltn/travelassistant/data/local/entity/ItineraryEntities.kt")
            .readText()
        val persistenceSource = appProjectDirectory
            .resolve("src/main/java/com/kltn/travelassistant/feature/itinerary/data")
            .walkTopDown()
            .filter(File::isFile)
            .filter { it.name.startsWith("SavedItinerary") || it.name ==
                "RoomSavedItineraryRepository.kt" }
            .joinToString(separator = "\n", transform = File::readText)

        listOf(
            "MediaRecorder",
            "AudioRecord",
            "FirebaseAnalytics",
            "FTS4",
            "FTS5",
            "MATCH",
            "AssistantQueryRepository",
            "ItineraryDraftGenerator",
            "latitude",
            "longitude",
            "Authorization",
            "token",
            "firebase_uid",
            "email",
        ).forEach { forbiddenToken ->
            assertFalse(
                "Room itinerary entities must not persist $forbiddenToken",
                entitySource.contains(forbiddenToken, ignoreCase = true),
            )
        }
        assertFalse(persistenceSource.contains("FirebaseAnalytics"))
        assertFalse(persistenceSource.contains("androidx.room.Fts"))
        assertFalse(persistenceSource.contains("AssistantQueryRepository"))
        assertFalse(persistenceSource.contains("/v1/itinerary-drafts/generate"))
        assertTrue(persistenceSource.contains("MAX_ATTEMPTS = 5"))
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

    private fun t070Source(): String {
        val featureDirectory = findAppProjectDirectory()
            .resolve("src/main/java/com/kltn/travelassistant/feature/itinerary")
        return listOf(
            featureDirectory.resolve("domain/ItineraryDraftModels.kt"),
            featureDirectory.resolve("domain/ItineraryDraftGenerator.kt"),
            featureDirectory.resolve("presentation/ItineraryFormValidator.kt"),
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
