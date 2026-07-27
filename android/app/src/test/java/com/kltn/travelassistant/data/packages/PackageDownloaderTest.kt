package com.kltn.travelassistant.data.packages

import com.kltn.travelassistant.feature.downloads.domain.PackageCity
import java.io.File
import kotlinx.coroutines.test.runTest
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import okhttp3.mockwebserver.SocketPolicy
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test

class PackageDownloaderTest {
    private lateinit var server: MockWebServer
    private val downloader = PackageDownloader(PackageHttpClient())

    @Before
    fun setUp() {
        server = MockWebServer()
        server.start()
    }

    @After
    fun tearDown() {
        server.shutdown()
    }

    @Test
    fun validDataDownloadSendsNoSensitiveHeadersOrUserContext() = runTest {
        server.enqueue(MockResponse().setBody(DATA))
        val destination = temporaryFile()

        downloader.downloadData(manifest(), destination)

        assertEquals(DATA, destination.readText())
        val request = server.takeRequest()
        assertNull(request.getHeader("Authorization"))
        assertNull(request.getHeader("X-Firebase-Token"))
        assertNull(request.requestUrl?.query)
    }

    @Test
    fun existingPartialUsesMatchingRangeAndAppendsValid206() = runTest {
        val partialSize = 7
        val dataByteSize = DATA.toByteArray().size
        val destination = temporaryFile(DATA.take(partialSize))
        server.enqueue(
            MockResponse()
                .setResponseCode(206)
                .setHeader(
                    "Content-Range",
                    "bytes $partialSize-${dataByteSize - 1}/$dataByteSize",
                )
                .setBody(DATA.drop(partialSize)),
        )

        downloader.downloadData(manifest(), destination)

        assertEquals(DATA, destination.readText())
        assertEquals("bytes=$partialSize-", server.takeRequest().getHeader("Range"))
    }

    @Test
    fun serverIgnoringRangeWith200RestartsFromByteZero() = runTest {
        val destination = temporaryFile("stale-partial")
        server.enqueue(MockResponse().setBody(DATA))

        downloader.downloadData(manifest(), destination)

        assertEquals(DATA, destination.readText())
        assertEquals("bytes=13-", server.takeRequest().getHeader("Range"))
    }

    @Test
    fun mismatchedContentRangeAndOversizedResponseAreRejected() = runTest {
        val dataByteSize = DATA.toByteArray().size
        run {
            val destination = temporaryFile(DATA.take(3))
            server.enqueue(
                MockResponse()
                    .setResponseCode(206)
                    .setHeader("Content-Range", "bytes 4-${dataByteSize - 1}/$dataByteSize")
                    .setBody(DATA.drop(4)),
            )

            val exception = expectPackageSyncException {
                downloader.downloadData(manifest(), destination)
            }
            assertEquals(PackageSyncError.INVALID_DATA, exception.error)
        }

        run {
            val destination = temporaryFile()
            server.enqueue(MockResponse().setBody("$DATA!"))

            val exception = expectPackageSyncException {
                downloader.downloadData(manifest(), destination)
            }
            assertEquals(PackageSyncError.INVALID_DATA, exception.error)
        }
    }

    @Test
    fun retryableServerResponseIsClassifiedWithoutWritingData() = runTest {
        server.enqueue(MockResponse().setResponseCode(503))
        val destination = temporaryFile()

        val exception = expectPackageSyncException {
            downloader.downloadData(manifest(), destination)
        }

        assertEquals(PackageSyncError.TEMPORARY_SERVER_FAILURE, exception.error)
        assertTrue(exception.error.retryable)
        assertEquals(0L, destination.length())
    }

    @Test
    fun interruptedBodyPreservesPartialBytesAndNextAttemptRestartsSafely() = runTest {
        val largeData = buildString {
            repeat(8_000) { append("Dữ liệu ngoại tuyến $it\n") }
        }
        val destination = temporaryFile()
        server.enqueue(
            MockResponse()
                .setBody(largeData)
                .setSocketPolicy(SocketPolicy.DISCONNECT_DURING_RESPONSE_BODY),
        )

        val interruption = expectPackageSyncException {
            downloader.downloadData(manifest(largeData), destination)
        }

        assertEquals(PackageSyncError.NETWORK_UNAVAILABLE, interruption.error)
        assertTrue(destination.length() in 1 until largeData.toByteArray().size.toLong())

        server.enqueue(MockResponse().setBody(largeData))
        downloader.downloadData(manifest(largeData), destination)

        assertEquals(largeData.toByteArray().size.toLong(), destination.length())
        assertEquals(largeData, destination.readText())
        assertTrue(server.takeRequest().getHeader("Range") == null)
        assertTrue(server.takeRequest().getHeader("Range")?.startsWith("bytes=") == true)
    }

    private fun manifest(data: String = DATA): ValidatedPackageManifest {
        val sha = java.security.MessageDigest.getInstance("SHA-256")
            .digest(data.toByteArray())
            .joinToString("") { "%02x".format(it) }
        val raw = """{"artifactSchemaVersion":1,"byteSize":${data.toByteArray().size},"city":"hcmc","contentVersion":"1.0.0","dataFilename":"hcmc-starter-v1-1.0.0.data.json","mediaType":"application/json","packageId":"hcmc-starter-v1","publishedAt":"2026-07-26T17:00:00Z","schemaVersion":1,"sha256":"$sha"}"""
        val location = PackageManifestLocation(
            city = PackageCity.HCMC,
            manifestUrl = server.url("/hcmc/manifest.json"),
            allowCleartext = true,
        )
        return PackageManifestValidator().validate(
            PackageManifestParser().parse(raw),
            raw,
            location,
        )
    }

    private fun temporaryFile(content: String = ""): File =
        kotlin.io.path.createTempFile().toFile().apply {
            writeText(content)
            deleteOnExit()
        }

    private suspend fun expectPackageSyncException(
        block: suspend () -> Unit,
    ): PackageSyncException = try {
        block()
        throw AssertionError("Expected PackageSyncException")
    } catch (exception: PackageSyncException) {
        exception
    }

    private companion object {
        const val DATA = "{\"value\":\"Tiếng Việt\"}\n"
    }
}
