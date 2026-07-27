package com.kltn.travelassistant.data.packages

import com.kltn.travelassistant.feature.downloads.domain.PackageCity
import okhttp3.HttpUrl.Companion.toHttpUrl
import org.junit.Assert.assertEquals
import org.junit.Assert.assertThrows
import org.junit.Test

class PackageManifestContractTest {
    private val parser = PackageManifestParser()
    private val validator = PackageManifestValidator()
    private val location = PackageManifestLocation(
        city = PackageCity.HCMC,
        manifestUrl = "https://packages.example.test/hcmc/manifest.json".toHttpUrl(),
    )

    @Test
    fun validManifestMatchesT034ContractAndResolvesSameOriginData() {
        val raw = validManifest()

        val result = validator.validate(parser.parse(raw), raw, location)

        assertEquals(1, result.document.schemaVersion)
        assertEquals("hcmc-starter-v1", result.document.packageId)
        assertEquals(
            "https://packages.example.test/hcmc/hcmc-starter-v1-1.0.0.data.json",
            result.dataUrl.toString(),
        )
        assertEquals(1_785_085_200_000L, result.publishedAtEpochMillis)
    }

    @Test
    fun unknownMalformedUnsafeAndCrossOriginFieldsAreRejected() {
        listOf(
            validManifest().replace(
                oldValue = """"schemaVersion":1""",
                newValue = """"schemaVersion":1,"unknown":true""",
            ),
            "{",
            validManifest().replace(
                "hcmc-starter-v1-1.0.0.data.json",
                "../hcmc-starter-v1-1.0.0.data.json",
            ),
            validManifest().replace(
                "hcmc-starter-v1-1.0.0.data.json",
                "https://evil.test/data.json",
            ),
        ).forEach { raw ->
            assertThrows(PackageSyncException::class.java) {
                validator.validate(parser.parse(raw), raw, location)
            }
        }
    }

    @Test
    fun unsupportedSchemaIdentityCityAndInsecureReleaseLocationAreRejected() {
        val unsupportedDocuments = listOf(
            parser.parse(validManifest().replace(""""schemaVersion":1""", """"schemaVersion":2""")),
            parser.parse(validManifest().replace(""""city":"hcmc"""", """"city":"bkk"""")),
            parser.parse(
                validManifest().replace(
                    """"packageId":"hcmc-starter-v1"""",
                    """"packageId":"hcmc-other-v1"""",
                ),
            ),
        )
        unsupportedDocuments.forEach { document ->
            assertThrows(PackageSyncException::class.java) {
                validator.validate(document, validManifest(), location)
            }
        }

        val cleartextLocation = location.copy(
            manifestUrl = "http://packages.example.test/manifest.json".toHttpUrl(),
        )
        assertThrows(PackageSyncException::class.java) {
            validator.validate(parser.parse(validManifest()), validManifest(), cleartextLocation)
        }
    }

    @Test
    fun uppercaseMalformedChecksumAndUnreasonableSizeAreRejected() {
        listOf(
            validManifest().replace(SHA256, SHA256.uppercase()),
            validManifest().replace(SHA256, "abc"),
            validManifest().replace(""""byteSize":934""", """"byteSize":0"""),
            validManifest().replace(
                """"byteSize":934""",
                """"byteSize":${PackageManifestValidator.MAX_ARTIFACT_BYTES + 1}""",
            ),
        ).forEach { raw ->
            assertThrows(PackageSyncException::class.java) {
                validator.validate(parser.parse(raw), raw, location)
            }
        }
    }

    @Test
    fun onlyTransientNetworkAndServerErrorsUseAutomaticRetry() {
        assertEquals(
            setOf(
                PackageSyncError.NETWORK_UNAVAILABLE,
                PackageSyncError.TEMPORARY_SERVER_FAILURE,
            ),
            PackageSyncError.entries.filter(PackageSyncError::retryable).toSet(),
        )
    }

    private fun validManifest(): String =
        """{"artifactSchemaVersion":1,"byteSize":934,"city":"hcmc","contentVersion":"1.0.0","dataFilename":"hcmc-starter-v1-1.0.0.data.json","mediaType":"application/json","packageId":"hcmc-starter-v1","publishedAt":"2026-07-26T17:00:00Z","schemaVersion":1,"sha256":"$SHA256"}"""

    private companion object {
        const val SHA256 = "daa7678e1998348c6904f12f6e96026aa7ac33068fab7d8dcdc2ec0b23ae6be3"
    }
}
