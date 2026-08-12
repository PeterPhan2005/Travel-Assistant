package com.kltn.travelassistant.feature.home

import java.io.File
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class DemoLocationReleaseSourcePolicyTest {
    @Test
    fun presetIdentitiesLabelsAndCoordinatesExistOnlyInDebugRuntimeSource() {
        val appDirectory = findAppDirectory()
        val debugSource = appDirectory.resolve(
            "src/debug/java/com/kltn/travelassistant/feature/home/domain/" +
                "DebugDemoLocationPresetProvider.kt",
        ).readText()
        val releaseProviderSource = appDirectory.resolve(
            "src/release/java/com/kltn/travelassistant/feature/home/domain/" +
                "ReleaseDemoLocationPresetProvider.kt",
        ).readText()
        val homeScreenSource = appDirectory.resolve(
            "src/main/java/com/kltn/travelassistant/feature/home/presentation/HomeScreen.kt",
        ).readText()
        val productionSources = listOf(
            appDirectory.resolve("src/main/java/com/kltn/travelassistant/feature/home"),
            appDirectory.resolve("src/main/java/com/kltn/travelassistant/MainActivity.kt"),
            appDirectory.resolve("src/main/java/com/kltn/travelassistant/TravelAssistantApp.kt"),
            appDirectory.resolve("src/main/java/com/kltn/travelassistant/navigation"),
            appDirectory.resolve("src/release/java"),
        ).flatMap { path ->
            if (path.isDirectory) path.walkTopDown().filter(File::isFile).toList() else listOf(path)
        }.filter { file -> file.extension == "kt" }
            .joinToString("\n", transform = File::readText)

        listOf(
            "Demo: TP.HCM",
            "Demo: Bangkok",
            "10.7799",
            "106.7",
            "13.746508",
            "100.493096",
        ).forEach { debugOnlyValue ->
            assertTrue(debugSource.contains(debugOnlyValue))
            assertFalse(productionSources.contains(debugOnlyValue))
        }
        assertTrue(releaseProviderSource.contains("override val presets: List<DemoLocationPreset> = emptyList()"))
        assertFalse(releaseProviderSource.contains("DeviceLocation"))
        assertTrue(homeScreenSource.contains("if (uiState.demoLocationPresets.isNotEmpty())"))
        assertFalse(productionSources.contains("BuildConfig.DEBUG"))
    }

    private fun findAppDirectory(): File {
        val workingDirectory = File(requireNotNull(System.getProperty("user.dir")))
        return listOf(
            workingDirectory,
            workingDirectory.resolve("app"),
            workingDirectory.resolve("android/app"),
        ).first { candidate ->
            candidate.resolve("build.gradle.kts").isFile && candidate.resolve("src").isDirectory
        }
    }
}
