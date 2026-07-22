package com.kltn.travelassistant.data.seed

import kotlinx.serialization.SerializationException
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json
import org.junit.Assert.assertEquals
import org.junit.Assert.assertThrows
import org.junit.Test

class SeedDocumentParserValidatorTest {
    private val parser = SeedDocumentParser()
    private val validator = SeedValidator(parser)

    @Test
    fun parserRejectsMalformedAndUnknownJson() {
        val validJson = Json.encodeToString(validDocument())
        val jsonWithUnknownField = validJson.dropLast(1) + ",\"unknown\":true}"

        assertThrows(SerializationException::class.java) { parser.parse("{") }
        assertThrows(SerializationException::class.java) { parser.parse(jsonWithUnknownField) }
    }

    @Test
    fun validatorMapsACompleteValidDocument() {
        val validated = validator.validate(validDocument())

        assertEquals(5, validated.pois.size)
        assertEquals(1, validated.aliases.size)
        assertEquals("bundled-hcmc-demo", validated.travelPackage.packageId)
    }

    @Test
    fun validatorRejectsDuplicateIdsInvalidCoordinatesAndNegativePrices() {
        val valid = validDocument()
        val duplicatePoi = valid.copy(pois = valid.pois + valid.pois.first())
        val invalidCoordinates = valid.copy(
            pois = valid.pois.mapIndexed { index, poi ->
                if (index == 0) poi.copy(latitude = 91.0) else poi
            },
        )
        val negativePrice = valid.copy(
            menuItems = listOf(
                SeedMenuItem(
                    menuItemId = "menu-1",
                    poiId = "poi-1",
                    dishName = "Dish",
                    priceMinorUnits = -1,
                    currencyCode = "VND",
                    sourceType = "curated",
                    updatedAtEpochMillis = 1,
                ),
            ),
        )

        assertThrows(SeedValidationException::class.java) { validator.validate(duplicatePoi) }
        assertThrows(SeedValidationException::class.java) { validator.validate(invalidCoordinates) }
        assertThrows(SeedValidationException::class.java) { validator.validate(negativePrice) }
    }

    @Test
    fun validatorRejectsInconsistentCityAndMissingParentReference() {
        val valid = validDocument()
        val inconsistentCity = valid.copy(
            pois = valid.pois.mapIndexed { index, poi ->
                if (index == 0) poi.copy(city = "HCMC") else poi
            },
        )
        val missingParent = valid.copy(
            aliases = valid.aliases.map { it.copy(poiId = "missing-poi") },
        )

        assertThrows(SeedValidationException::class.java) { validator.validate(inconsistentCity) }
        assertThrows(SeedValidationException::class.java) { validator.validate(missingParent) }
    }

    @Test
    fun narrationSourceLabelIsOptionalButCannotBeBlankWhenSupplied() {
        val valid = validDocument()
        val narration = SeedNarration(
            narrationId = "narration-1",
            poiId = "poi-1",
            languageCode = "vi",
            content = "Nội dung có nguồn.",
            verificationStatus = "verified",
            generatedAtEpochMillis = 1,
            sourceLabel = "Ban quản lý điểm đến",
        )

        val mapped = validator.validate(valid.copy(narrations = listOf(narration)))

        assertEquals("Ban quản lý điểm đến", mapped.narrations.single().sourceLabel)
        assertThrows(SeedValidationException::class.java) {
            validator.validate(
                valid.copy(narrations = listOf(narration.copy(sourceLabel = " "))),
            )
        }
    }

    private fun validDocument(): SeedDocument {
        val pois = (1..5).map { number ->
            SeedPoi(
                poiId = "poi-$number",
                name = "POI $number",
                city = SeedValidator.SUPPORTED_CITY,
                category = "test",
                latitude = 10.0 + number,
                longitude = 106.0,
                status = "demo",
                updatedAtEpochMillis = 1,
            )
        }
        return SeedDocument(
            formatVersion = SeedValidator.SUPPORTED_FORMAT_VERSION,
            packageMetadata = SeedPackageMetadata(
                packageId = "bundled-hcmc-demo",
                city = SeedValidator.SUPPORTED_CITY,
                version = "1",
                publishedAtEpochMillis = 1,
                manifest = SeedManifest(
                    formatVersion = SeedValidator.SUPPORTED_FORMAT_VERSION,
                    poiIds = pois.map(SeedPoi::poiId),
                ),
            ),
            pois = pois,
            aliases = listOf(
                SeedPoiAlias(
                    aliasId = "alias-1",
                    poiId = "poi-1",
                    alias = "Alias",
                    normalizedAlias = "alias",
                ),
            ),
        )
    }
}
