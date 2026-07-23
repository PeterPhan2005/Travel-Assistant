package com.kltn.travelassistant

import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.google.firebase.FirebaseApp
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class FirebaseInitializationTest {
    @Test
    fun defaultFirebaseAppInitializesFromDebugConfiguration() {
        val targetContext = InstrumentationRegistry.getInstrumentation().targetContext
        val firebaseApp = FirebaseApp.getInstance()
        val options = firebaseApp.options

        assertEquals("com.kltn.travelassistant", targetContext.packageName)
        assertEquals(targetContext.packageName, firebaseApp.applicationContext.packageName)
        assertFalse(options.applicationId.isBlank())
        assertFalse(options.apiKey.isBlank())
        assertFalse(options.projectId.isNullOrBlank())
        assertFalse(options.gcmSenderId.isNullOrBlank())
    }
}
