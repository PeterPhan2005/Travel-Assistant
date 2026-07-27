package com.kltn.travelassistant.data.packages

import com.kltn.travelassistant.feature.downloads.domain.PackageCity
import java.io.File
import okhttp3.HttpUrl.Companion.toHttpUrl
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertThrows
import org.junit.Assert.assertTrue
import org.junit.Test

class PackageArtifactContractTest {
    private val artifactParser = PackageArtifactParser()
    private val artifactValidator = PackageArtifactValidator()
    private val checksumVerifier = PackageChecksumVerifier()

    @Test
    fun committedT034ArtifactHasExactKnownChecksumAndMapsTwoUnicodePois() {
        val dataFile = committedDataFile()
        val manifest = committedManifest()

        assertEquals(934L, dataFile.length())
        assertTrue(checksumVerifier.verify(dataFile, manifest))
        val validated = artifactValidator.validate(artifactParser.parse(dataFile), manifest)

        assertEquals(2, validated.pois.size)
        assertEquals(0, validated.aliases.size)
        assertEquals(0, validated.menuItems.size)
        assertEquals(0, validated.narrations.size)
        assertEquals("Bưu điện Trung tâm Sài Gòn", validated.pois.first().name)
        assertEquals("hcmc-starter-v1", validated.metadata.packageId)
        assertEquals("1.0.0", validated.metadata.version)
    }

    @Test
    fun oneByteModificationAndWrongSizeNeverVerify() {
        val original = committedDataFile().readBytes()
        val modified = temporaryFile(original.copyOf().also { bytes ->
            bytes[bytes.lastIndex - 1] = (bytes[bytes.lastIndex - 1].toInt() xor 1).toByte()
        })
        val truncated = temporaryFile(original.copyOf(original.size - 1))

        assertFalse(checksumVerifier.verify(modified, committedManifest()))
        assertFalse(checksumVerifier.verify(truncated, committedManifest()))
    }

    @Test
    fun malformedUnknownAndIdentityMismatchedArtifactIsRejected() {
        val original = committedDataFile().readText()
        val candidates = listOf(
            "{",
            original.replace(
                oldValue = """"formatVersion":1""",
                newValue = """"formatVersion":1,"providerPayload":{}""",
            ),
            original.replace(
                """"packageId":"hcmc-starter-v1"""",
                """"packageId":"hcmc-other-v1"""",
            ),
            original.replace(
                """"version":"1.0.0"""",
                """"version":"2.0.0"""",
            ),
        )

        candidates.forEach { raw ->
            assertThrows(PackageSyncException::class.java) {
                val parsed = artifactParser.parse(temporaryFile(raw.toByteArray()))
                artifactValidator.validate(parsed, committedManifest())
            }
        }
    }

    private fun committedManifest(): ValidatedPackageManifest {
        val raw = committedManifestFile().readText()
        val location = PackageManifestLocation(
            city = PackageCity.HCMC,
            manifestUrl = "https://packages.example.test/hcmc/manifest.json".toHttpUrl(),
        )
        return PackageManifestValidator().validate(
            PackageManifestParser().parse(raw),
            raw,
            location,
        )
    }

    private fun committedDataFile(): File = repositoryFile(
        "data/travel-packages/hcmc/1.0.0/hcmc-starter-v1-1.0.0.data.json",
    )

    private fun committedManifestFile(): File = repositoryFile(
        "data/travel-packages/hcmc/1.0.0/hcmc-starter-v1-1.0.0.manifest.json",
    )

    private fun repositoryFile(relativePath: String): File =
        generateSequence(File(requireNotNull(System.getProperty("user.dir")))) { it.parentFile }
            .map { it.resolve(relativePath) }
            .first(File::isFile)

    private fun temporaryFile(bytes: ByteArray): File =
        kotlin.io.path.createTempFile().toFile().apply {
            writeBytes(bytes)
            deleteOnExit()
        }
}
