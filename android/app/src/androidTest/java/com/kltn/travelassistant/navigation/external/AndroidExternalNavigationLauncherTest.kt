package com.kltn.travelassistant.navigation.external

import android.content.ActivityNotFoundException
import android.content.Intent
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.kltn.travelassistant.feature.poi.domain.PoiNavigationTarget
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class AndroidExternalNavigationLauncherTest {
    @Test
    fun createsGenericLocaleIndependentGeoIntentAndEncodesDisplayName() {
        val launcher = AndroidExternalNavigationLauncher(RecordingGateway())

        val intent = launcher.createMapIntent(target)
        val uri = requireNotNull(intent.data)
        val uriText = uri.toString()

        assertEquals(Intent.ACTION_VIEW, intent.action)
        assertEquals("geo", uri.scheme)
        assertTrue(intent.flags and Intent.FLAG_ACTIVITY_NEW_TASK != 0)
        assertTrue(uriText, uriText.startsWith("geo:10.1234567890123,106.987654321098?q="))
        assertTrue(uriText, uriText.contains("10.1234567890123,106.987654321098"))
        assertTrue(uriText, uriText.contains("Ch%E1%BB%A3%20%26%20%28c%E1%BB%ADa%29"))
        assertFalse(uriText.contains(target.displayName))
    }

    @Test
    fun invalidTargetReturnsControlledErrorWithoutResolvingOrLaunching() {
        val gateway = RecordingGateway()
        val launcher = AndroidExternalNavigationLauncher(gateway)

        val result = launcher.open(target.copy(latitude = Double.NaN))

        assertEquals(ExternalNavigationResult.InvalidDestination, result)
        assertEquals(0, gateway.resolveRequests)
        assertNull(gateway.startedIntent)
    }

    @Test
    fun missingCompatibleApplicationDoesNotLaunch() {
        val gateway = RecordingGateway(canOpen = false)
        val launcher = AndroidExternalNavigationLauncher(gateway)

        assertEquals(ExternalNavigationResult.NoCompatibleApplication, launcher.open(target))
        assertEquals(1, gateway.resolveRequests)
        assertNull(gateway.startedIntent)
    }

    @Test
    fun resolvedApplicationIsOpenedWithGenericIntent() {
        val gateway = RecordingGateway()
        val launcher = AndroidExternalNavigationLauncher(gateway)

        assertEquals(ExternalNavigationResult.Opened, launcher.open(target))
        assertEquals(Intent.ACTION_VIEW, gateway.startedIntent?.action)
        assertEquals("geo", gateway.startedIntent?.data?.scheme)
        assertNull(gateway.startedIntent?.`package`)
    }

    @Test
    fun applicationDisappearingAfterResolutionReturnsUnavailable() {
        val gateway = RecordingGateway(
            launchFailure = ActivityNotFoundException("Expected test failure"),
        )
        val launcher = AndroidExternalNavigationLauncher(gateway)

        assertEquals(ExternalNavigationResult.NoCompatibleApplication, launcher.open(target))
    }

    @Test
    fun securityFailureReturnsControlledLaunchFailure() {
        val gateway = RecordingGateway(
            launchFailure = SecurityException("Expected test failure"),
        )
        val launcher = AndroidExternalNavigationLauncher(gateway)

        assertEquals(ExternalNavigationResult.LaunchFailed, launcher.open(target))
    }

    private class RecordingGateway(
        private val canOpen: Boolean = true,
        private val launchFailure: RuntimeException? = null,
    ) : ExternalMapActivityGateway {
        var resolveRequests = 0
        var startedIntent: Intent? = null

        override fun canOpen(intent: Intent): Boolean {
            resolveRequests += 1
            return canOpen
        }

        override fun open(intent: Intent) {
            launchFailure?.let { throw it }
            startedIntent = intent
        }
    }

    private companion object {
        val target = PoiNavigationTarget(
            poiId = "central-post-office",
            displayName = "Chợ & (cửa)",
            latitude = 10.1234567890123,
            longitude = 106.987654321098,
        )
    }
}
