package com.kltn.travelassistant.feature.itinerary.data

import android.content.Context
import androidx.work.BackoffPolicy
import androidx.work.Constraints
import androidx.work.Data
import androidx.work.ExistingWorkPolicy
import androidx.work.NetworkType
import androidx.work.OneTimeWorkRequest
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.WorkManager
import dagger.hilt.android.qualifiers.ApplicationContext
import java.util.UUID
import java.util.concurrent.TimeUnit
import javax.inject.Inject
import javax.inject.Singleton

internal interface ItineraryWorkScheduler {
    fun enqueue(itineraryId: String)
}

@Singleton
internal class WorkManagerItineraryScheduler @Inject constructor(
    @ApplicationContext context: Context,
    private val requestFactory: SavedItineraryWorkRequestFactory,
) : ItineraryWorkScheduler {
    private val workManager = WorkManager.getInstance(context)

    override fun enqueue(itineraryId: String) {
        require(UUID.fromString(itineraryId).toString() == itineraryId)
        workManager.enqueueUniqueWork(
            uniqueWorkName(itineraryId),
            ExistingWorkPolicy.REPLACE,
            requestFactory.create(itineraryId),
        )
    }

    companion object {
        const val WORK_TAG = "itinerary-sync"

        fun uniqueWorkName(itineraryId: String): String = "itinerary-sync-$itineraryId"
    }
}

internal class SavedItineraryWorkRequestFactory @Inject constructor() {
    fun create(itineraryId: String): OneTimeWorkRequest {
        require(UUID.fromString(itineraryId).toString() == itineraryId)
        return OneTimeWorkRequestBuilder<SavedItinerarySyncWorker>()
            .setConstraints(
                Constraints.Builder()
                    .setRequiredNetworkType(NetworkType.CONNECTED)
                    .build(),
            )
            .setBackoffCriteria(
                BackoffPolicy.EXPONENTIAL,
                INITIAL_BACKOFF_SECONDS,
                TimeUnit.SECONDS,
            )
            .setInputData(
                Data.Builder()
                    .putString(SavedItinerarySyncWorker.KEY_ITINERARY_ID, itineraryId)
                    .build(),
            )
            .addTag(WorkManagerItineraryScheduler.WORK_TAG)
            .build()
    }

    companion object {
        const val INITIAL_BACKOFF_SECONDS = 30L
    }
}
