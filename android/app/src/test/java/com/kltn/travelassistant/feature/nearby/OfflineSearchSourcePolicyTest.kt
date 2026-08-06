package com.kltn.travelassistant.feature.nearby

import java.io.File
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class OfflineSearchSourcePolicyTest {
    @Test
    fun offlineSearchHasNoTransportModelAnalyticsOrLoggingBoundary() {
        val source = offlineSearchSource()

        assertTrue(source.contains("@Fts4"))
        assertTrue(source.contains("local_poi_search_fts MATCH :matchExpression"))
        listOf(
            "okhttp3",
            "Retrofit",
            "Firebase",
            "OpenAI",
            "Analytics",
            "android.util.Log",
            "Authorization",
            "Bearer",
            "token request",
        ).forEach { forbiddenToken ->
            assertFalse(
                "Offline search must not use $forbiddenToken",
                source.contains(forbiddenToken, ignoreCase = true),
            )
        }
    }

    private fun offlineSearchSource(): String {
        val appProjectDirectory = findAppProjectDirectory()
        val relativeFiles = listOf(
            "src/main/java/com/kltn/travelassistant/data/local/PoiSearchIndexBuilder.kt",
            "src/main/java/com/kltn/travelassistant/data/local/dao/PoiContentDao.kt",
            "src/main/java/com/kltn/travelassistant/data/local/entity/LocalPoiSearchFtsEntity.kt",
            "src/main/java/com/kltn/travelassistant/data/repository/RoomNearbySearchRepository.kt",
            "src/main/java/com/kltn/travelassistant/feature/nearby/domain/OfflineSearchQueryCompiler.kt",
        )
        return relativeFiles.joinToString(separator = "\n") { relativePath ->
            appProjectDirectory.resolve(relativePath).readText()
        }
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
}
