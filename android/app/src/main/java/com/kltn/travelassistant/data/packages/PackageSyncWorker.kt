package com.kltn.travelassistant.data.packages

import android.content.Context
import android.util.Log
import androidx.hilt.work.HiltWorker
import androidx.work.CoroutineWorker
import androidx.work.Data
import androidx.work.WorkerParameters
import com.kltn.travelassistant.feature.downloads.domain.PackageCity
import com.kltn.travelassistant.feature.downloads.domain.PackageSyncPhase
import dagger.assisted.Assisted
import dagger.assisted.AssistedInject
import kotlinx.coroutines.CancellationException

@HiltWorker
class PackageSyncWorker @AssistedInject constructor(
    @Assisted appContext: Context,
    @Assisted workerParameters: WorkerParameters,
    private val engine: PackageSyncEngine,
) : CoroutineWorker(appContext, workerParameters) {
    override suspend fun doWork(): Result {
        val city = inputData.getString(KEY_CITY_CODE)
            ?.let { code -> PackageCity.entries.firstOrNull { it.code == code } }
            ?: return Result.failure(failureData(PackageSyncError.UNSUPPORTED_PACKAGE))
        return try {
            engine.synchronize(city) { phase ->
                setProgress(progressData(phase))
            }
            Result.success(
                Data.Builder()
                    .putString(KEY_CITY_CODE, city.code)
                    .build(),
            )
        } catch (exception: CancellationException) {
            throw exception
        } catch (exception: PackageSyncException) {
            Log.w(TAG, "Package sync failed (${exception.error.name.lowercase()})")
            if (exception.error.retryable) {
                Result.retry()
            } else {
                Result.failure(failureData(exception.error))
            }
        } catch (_: Exception) {
            Log.w(TAG, "Package sync failed (unexpected)")
            Result.failure(failureData(PackageSyncError.ACTIVATION_FAILED))
        }
    }

    companion object {
        const val KEY_CITY_CODE = "city_code"
        const val KEY_PHASE = "phase"
        const val KEY_FAILURE_CODE = "failure_code"
        private const val TAG = "TravelPackageSync"

        fun progressData(phase: PackageSyncPhase): Data = Data.Builder()
            .putString(KEY_PHASE, phase.name)
            .build()

        fun failureData(error: PackageSyncError): Data = Data.Builder()
            .putString(KEY_FAILURE_CODE, error.name)
            .build()
    }
}
