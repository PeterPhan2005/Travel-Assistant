package com.kltn.travelassistant.feature.itinerary.data

import android.content.Context
import android.util.Log
import androidx.hilt.work.HiltWorker
import androidx.work.CoroutineWorker
import androidx.work.Data
import androidx.work.WorkerParameters
import dagger.assisted.Assisted
import dagger.assisted.AssistedInject
import kotlinx.coroutines.CancellationException

@HiltWorker
internal class SavedItinerarySyncWorker @AssistedInject constructor(
    @Assisted appContext: Context,
    @Assisted workerParameters: WorkerParameters,
    private val engine: SavedItinerarySyncEngine,
) : CoroutineWorker(appContext, workerParameters) {
    override suspend fun doWork(): Result {
        val itineraryId = inputData.getString(KEY_ITINERARY_ID)
            ?: return terminal(ItinerarySyncOutcome.INVALID_DATA)
        return try {
            when (val outcome = engine.synchronize(itineraryId)) {
                ItinerarySyncOutcome.SUCCESS -> Result.success()
                ItinerarySyncOutcome.NEWER_LOCAL_REVISION,
                ItinerarySyncOutcome.RETRYABLE_FAILURE,
                -> if (runAttemptCount + 1 >= MAX_ATTEMPTS) {
                    engine.markRetryExhausted(itineraryId)
                    terminal(ItinerarySyncOutcome.RETRYABLE_FAILURE)
                } else {
                    Result.retry()
                }
                ItinerarySyncOutcome.CONFLICT,
                ItinerarySyncOutcome.AUTHENTICATION_FAILURE,
                ItinerarySyncOutcome.INVALID_DATA,
                -> terminal(outcome)
            }
        } catch (exception: CancellationException) {
            throw exception
        } catch (exception: Exception) {
            if (runAttemptCount + 1 >= MAX_ATTEMPTS) {
                engine.markRetryExhausted(itineraryId)
                terminal(ItinerarySyncOutcome.RETRYABLE_FAILURE)
            } else {
                Result.retry()
            }
        }
    }

    private fun terminal(outcome: ItinerarySyncOutcome): Result {
        Log.w(TAG, "Saved itinerary sync ended (${outcome.name.lowercase()})")
        return Result.failure(
            Data.Builder().putString(KEY_FAILURE_CODE, outcome.name).build(),
        )
    }

    companion object {
        const val KEY_ITINERARY_ID = "itinerary_id"
        const val KEY_FAILURE_CODE = "failure_code"
        const val MAX_ATTEMPTS = 5
        private const val TAG = "ItinerarySync"
    }
}
