package com.kltn.travelassistant.data.preferences

import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.work.BackoffPolicy
import androidx.work.NetworkType
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class PreferenceWorkRequestFactoryTest {
    @Test
    fun requestIsUniqueConnectedExponentialAndContainsNoPrivateData() {
        val request = PreferenceWorkRequestFactory().create()

        assertEquals("preference-sync", WorkManagerPreferenceScheduler.UNIQUE_WORK_NAME)
        assertTrue(request.tags.contains(WorkManagerPreferenceScheduler.WORK_TAG))
        assertTrue(request.workSpec.input.keyValueMap.isEmpty())
        assertEquals(
            NetworkType.CONNECTED,
            request.workSpec.constraints.requiredNetworkType,
        )
        assertEquals(BackoffPolicy.EXPONENTIAL, request.workSpec.backoffPolicy)
        assertEquals(
            PreferenceWorkRequestFactory.INITIAL_BACKOFF_SECONDS * 1_000,
            request.workSpec.backoffDelayDuration,
        )

        val failure = PreferenceSyncWorker.failureData(
            PreferenceSyncOutcome.AUTHENTICATION_FAILURE,
        )
        assertEquals(setOf(PreferenceSyncWorker.KEY_FAILURE_CODE), failure.keyValueMap.keys)
        val serialized = failure.keyValueMap.values.joinToString(" ").lowercase()
        assertFalse(serialized.contains("token"))
        assertFalse(serialized.contains("uid"))
        assertFalse(serialized.contains("{"))
    }
}

