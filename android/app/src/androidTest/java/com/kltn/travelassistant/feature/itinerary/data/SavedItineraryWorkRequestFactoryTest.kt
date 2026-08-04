package com.kltn.travelassistant.feature.itinerary.data

import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.work.NetworkType
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class SavedItineraryWorkRequestFactoryTest {
    @Test
    fun workContainsOnlyStableIdWithNetworkConstraintAndBoundedBackoff() {
        val request = SavedItineraryWorkRequestFactory().create(ITINERARY_ID)

        assertEquals(
            setOf(SavedItinerarySyncWorker.KEY_ITINERARY_ID),
            request.workSpec.input.keyValueMap.keys,
        )
        assertEquals(
            ITINERARY_ID,
            request.workSpec.input.getString(SavedItinerarySyncWorker.KEY_ITINERARY_ID),
        )
        assertEquals(NetworkType.CONNECTED, request.workSpec.constraints.requiredNetworkType)
        assertEquals(
            SavedItineraryWorkRequestFactory.INITIAL_BACKOFF_SECONDS * 1_000,
            request.workSpec.backoffDelayDuration,
        )
        assertTrue(request.tags.contains(WorkManagerItineraryScheduler.WORK_TAG))
        assertFalse(request.workSpec.input.keyValueMap.toString().contains("token"))
        assertFalse(request.workSpec.input.keyValueMap.toString().contains("account"))
        assertEquals(
            "itinerary-sync-$ITINERARY_ID",
            WorkManagerItineraryScheduler.uniqueWorkName(ITINERARY_ID),
        )
        assertEquals(5, SavedItinerarySyncWorker.MAX_ATTEMPTS)
    }

    private companion object {
        const val ITINERARY_ID = "00000000-0000-4000-8000-000000000071"
    }
}
