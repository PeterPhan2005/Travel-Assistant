package com.kltn.travelassistant.data.packages

import com.kltn.travelassistant.feature.downloads.domain.PackageCity
import com.kltn.travelassistant.feature.downloads.domain.PackageSyncPhase
import java.io.File
import java.security.MessageDigest
import kotlinx.coroutines.test.runTest
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test

class PackageSyncEngineTest {
    private lateinit var server: MockWebServer
    private lateinit var root: File

    @Before
    fun setUp() {
        server = MockWebServer()
        server.start()
        root = kotlin.io.path.createTempDirectory().toFile()
    }

    @After
    fun tearDown() {
        server.shutdown()
        root.deleteRecursively()
    }

    @Test
    fun validVerifiedArtifactActivatesOnlyAfterAllProgressPhases() = runTest {
        val data = committedDataFile().readText()
        server.enqueue(MockResponse().setBody(manifestFor(data)))
        server.enqueue(MockResponse().setBody(data))
        var activated: ValidatedTravelPackage? = null
        val phases = mutableListOf<PackageSyncPhase>()
        val engine = engine(
            activator = PackageActivator { travelPackage ->
                activated = travelPackage
                PackageActivationResult.ACTIVATED
            },
        )

        engine.synchronize(PackageCity.HCMC, phases::add)

        assertEquals(2, activated?.pois?.size)
        assertEquals("Bưu điện Trung tâm Sài Gòn", activated?.pois?.first()?.name)
        assertEquals(
            listOf(
                PackageSyncPhase.DOWNLOADING_MANIFEST,
                PackageSyncPhase.DOWNLOADING_DATA,
                PackageSyncPhase.VERIFYING,
                PackageSyncPhase.VALIDATING,
                PackageSyncPhase.ACTIVATING,
            ),
            phases,
        )
        assertTrue(root.walkTopDown().filter(File::isFile).none())
    }

    @Test
    fun checksumMismatchNeverReachesActivatorAndCleansInvalidStage() = runTest {
        val validData = committedDataFile().readText()
        val modifiedData = validData.replace("Bưu điện", "Xưu điện")
        server.enqueue(MockResponse().setBody(manifestFor(validData)))
        server.enqueue(MockResponse().setBody(modifiedData))
        var activationCount = 0
        val engine = engine(
            activator = PackageActivator {
                activationCount += 1
                PackageActivationResult.ACTIVATED
            },
        )

        val exception = try {
            engine.synchronize(PackageCity.HCMC) {}
            throw AssertionError("Expected PackageSyncException")
        } catch (error: PackageSyncException) {
            error
        }

        assertEquals(PackageSyncError.CHECKSUM_MISMATCH, exception.error)
        assertEquals(0, activationCount)
        assertTrue(root.walkTopDown().filter(File::isFile).none())
    }

    private fun engine(activator: PackageActivator): PackageSyncEngine {
        val location = PackageManifestLocation(
            city = PackageCity.HCMC,
            manifestUrl = server.url("/hcmc-starter-v1-1.0.0.manifest.json"),
            allowCleartext = true,
        )
        return PackageSyncEngine(
            locationProvider = PackageManifestLocationProvider { location },
            downloader = PackageDownloader(PackageHttpClient()),
            manifestParser = PackageManifestParser(),
            manifestValidator = PackageManifestValidator(),
            stagingStore = PackageStagingStore(root),
            checksumVerifier = PackageChecksumVerifier(),
            artifactParser = PackageArtifactParser(),
            artifactValidator = PackageArtifactValidator(),
            activator = activator,
        )
    }

    private fun manifestFor(data: String): String {
        val bytes = data.toByteArray()
        val sha = MessageDigest.getInstance("SHA-256")
            .digest(bytes)
            .joinToString("") { "%02x".format(it) }
        return """{"artifactSchemaVersion":1,"byteSize":${bytes.size},"city":"hcmc","contentVersion":"1.0.0","dataFilename":"hcmc-starter-v1-1.0.0.data.json","mediaType":"application/json","packageId":"hcmc-starter-v1","publishedAt":"2026-07-26T17:00:00Z","schemaVersion":1,"sha256":"$sha"}"""
    }

    private fun committedDataFile(): File =
        generateSequence(File(requireNotNull(System.getProperty("user.dir")))) { it.parentFile }
            .map {
                it.resolve(
                    "data/travel-packages/hcmc/1.0.0/" +
                        "hcmc-starter-v1-1.0.0.data.json",
                )
            }
            .first(File::isFile)
}
