package com.kltn.travelassistant.navigation

import androidx.annotation.StringRes
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.List
import androidx.compose.material.icons.filled.Face
import androidx.compose.material.icons.filled.KeyboardArrowDown
import androidx.compose.material.icons.filled.Person
import androidx.compose.material.icons.filled.Place
import androidx.compose.ui.graphics.vector.ImageVector
import com.kltn.travelassistant.R

enum class TopLevelDestination(
    val route: String,
    @param:StringRes val labelRes: Int,
    @param:StringRes val iconContentDescriptionRes: Int,
    val icon: ImageVector,
) {
    EXPLORE(
        route = "explore",
        labelRes = R.string.destination_explore,
        iconContentDescriptionRes = R.string.open_explore,
        icon = Icons.Filled.Place,
    ),
    ASSISTANT(
        route = "assistant",
        labelRes = R.string.destination_assistant,
        iconContentDescriptionRes = R.string.open_assistant,
        icon = Icons.Filled.Face,
    ),
    ITINERARY(
        route = "itinerary",
        labelRes = R.string.destination_itinerary,
        iconContentDescriptionRes = R.string.open_itinerary,
        icon = Icons.AutoMirrored.Filled.List,
    ),
    DOWNLOADS(
        route = "downloads",
        labelRes = R.string.destination_downloads,
        iconContentDescriptionRes = R.string.open_downloads,
        icon = Icons.Filled.KeyboardArrowDown,
    ),
    PROFILE(
        route = "profile",
        labelRes = R.string.destination_profile,
        iconContentDescriptionRes = R.string.open_profile,
        icon = Icons.Filled.Person,
    ),
    ;

    companion object {
        val all: List<TopLevelDestination> = entries
        val startDestination: TopLevelDestination = EXPLORE

        fun fromRoute(route: String?): TopLevelDestination? =
            entries.firstOrNull { destination -> destination.route == route }
    }
}
