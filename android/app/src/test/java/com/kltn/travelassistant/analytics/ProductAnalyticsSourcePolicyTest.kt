package com.kltn.travelassistant.analytics

import java.io.File
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class ProductAnalyticsSourcePolicyTest {
    @Test
    fun analyticsHasNoVendorNetworkPersistenceIdentityLocationOrContentBoundary() {
        val source = analyticsSource()

        assertTrue(source.contains("sealed interface ProductAnalyticsEvent"))
        assertTrue(source.contains("BuildConfig.DEBUG"))
        listOf(
            "FirebaseAnalytics",
            "FirebaseAuth",
            "OpenAI",
            "okhttp3",
            "retrofit2",
            "WorkManager",
            "RoomDatabase",
            "DataStore",
            "SharedPreferences",
            "java.io.File",
            "android.util.Log",
            "latitude",
            "longitude",
            "transcript",
            "queryText",
            "Authorization",
            "accessToken",
            "idToken",
            "firebaseUid",
            "email",
            "exception.message",
            "stackTrace",
        ).forEach { forbidden ->
            assertFalse(
                "Analytics source must not contain $forbidden",
                source.contains(forbidden, ignoreCase = true),
            )
        }
    }

    private fun analyticsSource(): String {
        val workingDirectory = File(requireNotNull(System.getProperty("user.dir")))
        val appDirectory = listOf(
            workingDirectory,
            workingDirectory.resolve("app"),
            workingDirectory.resolve("android/app"),
        ).first { candidate ->
            candidate.resolve("build.gradle.kts").isFile && candidate.resolve("src").isDirectory
        }
        return listOf(
            appDirectory.resolve("src/main/java/com/kltn/travelassistant/analytics"),
            appDirectory.resolve("src/main/java/com/kltn/travelassistant/di/ProductAnalyticsModule.kt"),
            appDirectory.resolve("src/debug/java/com/kltn/travelassistant/analytics"),
        ).flatMap { path ->
            if (path.isDirectory) path.walkTopDown().filter(File::isFile).toList() else listOf(path)
        }.filter { it.extension == "kt" }
            .sortedBy(File::getPath)
            .joinToString("\n", transform = File::readText)
    }
}
