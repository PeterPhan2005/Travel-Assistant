package com.kltn.travelassistant

import java.io.File
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class FirebaseConfigurationPolicyTest {
    @Test
    fun onlyDebugConfigurationIsPresentAndMatchesApplicationId() {
        val appProjectDirectory = findAppProjectDirectory()
        val debugConfiguration = appProjectDirectory.resolve("src/debug/google-services.json")

        assertTrue("Debug Firebase configuration must be available", debugConfiguration.isFile)

        val document = Json.parseToJsonElement(debugConfiguration.readText()).jsonObject
        val configuredPackages = document.getValue("client")
            .jsonArray
            .map { client ->
                client.jsonObject
                    .getValue("client_info")
                    .jsonObject
                    .getValue("android_client_info")
                    .jsonObject
                    .getValue("package_name")
                    .jsonPrimitive
                    .content
            }

        assertTrue("At least one Android Firebase client must be configured", configuredPackages.isNotEmpty())
        assertTrue(
            "Every Firebase Android client must match the application ID",
            configuredPackages.all { it == APPLICATION_ID },
        )

        disallowedConfigurationLocations(appProjectDirectory).forEach { disallowedFile ->
            assertFalse(
                "Firebase configuration must remain debug-specific: ${disallowedFile.path}",
                disallowedFile.exists(),
            )
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

    private fun disallowedConfigurationLocations(appProjectDirectory: File): List<File> {
        val androidProjectDirectory = requireNotNull(appProjectDirectory.parentFile)
        val repositoryDirectory = requireNotNull(androidProjectDirectory.parentFile)
        return listOf(
            appProjectDirectory.resolve("google-services.json"),
            appProjectDirectory.resolve("src/main/google-services.json"),
            appProjectDirectory.resolve("src/release/google-services.json"),
            appProjectDirectory.resolve("src/production/google-services.json"),
            appProjectDirectory.resolve("src/staging/google-services.json"),
            appProjectDirectory.resolve("src/local/google-services.json"),
            androidProjectDirectory.resolve("google-services.json"),
            repositoryDirectory.resolve("google-services.json"),
        )
    }

    private companion object {
        const val APPLICATION_ID = "com.kltn.travelassistant"
    }
}
