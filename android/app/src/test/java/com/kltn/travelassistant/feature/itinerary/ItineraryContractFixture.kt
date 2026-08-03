package com.kltn.travelassistant.feature.itinerary

import java.io.File

internal fun readItineraryContractFixture(name: String): String {
    val workingDirectory = File(requireNotNull(System.getProperty("user.dir")))
    val fixture = generateSequence(workingDirectory, File::getParentFile)
        .take(6)
        .map { directory ->
            directory.resolve("contracts/fixtures/$name")
        }
        .firstOrNull(File::isFile)
        ?: error("Unable to locate shared itinerary contract fixture: $name")
    return fixture.readText(Charsets.UTF_8).trim()
}
