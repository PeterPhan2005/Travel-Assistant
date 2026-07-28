package com.kltn.travelassistant.data.preferences

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
internal class PreferenceSyncWorker @AssistedInject constructor(
    @Assisted appContext: Context,
    @Assisted workerParameters: WorkerParameters,
    private val engine: PreferenceSyncEngine,
) : CoroutineWorker(appContext, workerParameters) {
    override suspend fun doWork(): Result = try {
        when (val outcome = engine.synchronizeCurrentAccount()) {
            PreferenceSyncOutcome.SUCCESS -> Result.success()
            PreferenceSyncOutcome.NEWER_LOCAL_REVISION,
            PreferenceSyncOutcome.RETRYABLE_FAILURE,
            -> Result.retry()
            PreferenceSyncOutcome.AUTHENTICATION_FAILURE,
            PreferenceSyncOutcome.INVALID_DOCUMENT,
            -> {
                Log.w(TAG, "Preference sync failed (${outcome.name.lowercase()})")
                Result.failure(failureData(outcome))
            }
        }
    } catch (exception: CancellationException) {
        throw exception
    } catch (exception: Exception) {
        Log.w(TAG, "Preference sync failed (unexpected)")
        Result.retry()
    }

    companion object {
        const val KEY_FAILURE_CODE = "failure_code"
        private const val TAG = "PreferenceSync"

        fun failureData(outcome: PreferenceSyncOutcome): Data = Data.Builder()
            .putString(KEY_FAILURE_CODE, outcome.name)
            .build()
    }
}

