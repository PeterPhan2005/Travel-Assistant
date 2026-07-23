package com.kltn.travelassistant.data.connectivity

import androidx.test.ext.junit.runners.AndroidJUnit4
import org.junit.Assert.assertEquals
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class AndroidConnectivityClassificationTest {
    @Test
    fun onlineRequiresBothInternetAndValidatedCapabilities() {
        assertEquals(ConnectivityStatus.OFFLINE, null.toConnectivityStatus())
        assertEquals(
            ConnectivityStatus.OFFLINE,
            classifyConnectivity(hasInternetCapability = true, hasValidatedCapability = false),
        )
        assertEquals(
            ConnectivityStatus.OFFLINE,
            classifyConnectivity(hasInternetCapability = false, hasValidatedCapability = true),
        )
        assertEquals(
            ConnectivityStatus.ONLINE,
            classifyConnectivity(hasInternetCapability = true, hasValidatedCapability = true),
        )
    }
}
