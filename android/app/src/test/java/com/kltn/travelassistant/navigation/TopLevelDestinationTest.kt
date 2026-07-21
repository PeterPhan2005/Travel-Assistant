package com.kltn.travelassistant.navigation

import org.junit.Assert.assertEquals
import org.junit.Test

class TopLevelDestinationTest {
    @Test
    fun allFiveTopLevelDestinationsAreDefined() {
        assertEquals(
            listOf("explore", "assistant", "itinerary", "downloads", "profile"),
            TopLevelDestination.all.map(TopLevelDestination::route),
        )
    }

    @Test
    fun routesAreUnique() {
        val routes = TopLevelDestination.all.map(TopLevelDestination::route)

        assertEquals(routes.size, routes.toSet().size)
    }

    @Test
    fun exploreIsTheStartDestination() {
        assertEquals(TopLevelDestination.EXPLORE, TopLevelDestination.startDestination)
        assertEquals("explore", TopLevelDestination.startDestination.route)
    }
}
