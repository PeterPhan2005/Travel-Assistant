package com.kltn.travelassistant

import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import org.junit.Assert.assertEquals
import org.junit.Test
import org.junit.runner.RunWith

/** Verifies that the installed scaffold retains its documented application ID. */
@RunWith(AndroidJUnit4::class)
class AndroidAppIdentityTest {
    @Test
    fun targetContextUsesTravelAssistantApplicationId() {
        val targetContext = InstrumentationRegistry.getInstrumentation().targetContext

        assertEquals("com.kltn.travelassistant", targetContext.packageName)
    }
}
