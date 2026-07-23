package com.kltn.travelassistant.navigation.external

import android.content.ActivityNotFoundException
import android.content.Intent
import android.net.Uri
import androidx.core.net.toUri
import com.kltn.travelassistant.feature.poi.domain.PoiNavigationTarget
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class AndroidExternalNavigationLauncher @Inject constructor(
    private val activityGateway: ExternalMapActivityGateway,
) : ExternalNavigationLauncher {
    override fun open(target: PoiNavigationTarget): ExternalNavigationResult {
        if (!target.isValidForExternalNavigation()) {
            return ExternalNavigationResult.InvalidDestination
        }

        val intent = try {
            createMapIntent(target)
        } catch (_: IllegalArgumentException) {
            return ExternalNavigationResult.InvalidDestination
        }

        return try {
            if (!activityGateway.canOpen(intent)) {
                ExternalNavigationResult.NoCompatibleApplication
            } else {
                activityGateway.open(intent)
                ExternalNavigationResult.Opened
            }
        } catch (_: ActivityNotFoundException) {
            ExternalNavigationResult.NoCompatibleApplication
        } catch (_: SecurityException) {
            ExternalNavigationResult.LaunchFailed
        } catch (_: IllegalArgumentException) {
            ExternalNavigationResult.InvalidDestination
        } catch (_: RuntimeException) {
            ExternalNavigationResult.LaunchFailed
        }
    }

    internal fun createMapIntent(target: PoiNavigationTarget): Intent {
        require(target.isValidForExternalNavigation())
        val latitude = target.latitude.toString()
        val longitude = target.longitude.toString()
        val encodedName = Uri.encode(target.displayName.trim())
            .replace("(", "%28")
            .replace(")", "%29")
        val uriString = "$GEO_SCHEME:$latitude,$longitude" +
            "?$QUERY_PARAMETER=$latitude,$longitude($encodedName)"
        val uri = uriString.toUri()
        return Intent(Intent.ACTION_VIEW, uri).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
    }

    private companion object {
        const val GEO_SCHEME = "geo"
        const val QUERY_PARAMETER = "q"
    }
}
