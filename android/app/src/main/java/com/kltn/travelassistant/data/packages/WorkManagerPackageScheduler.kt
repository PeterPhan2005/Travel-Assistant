package com.kltn.travelassistant.data.packages

import android.content.Context
import androidx.work.BackoffPolicy
import androidx.work.Constraints
import androidx.work.ExistingWorkPolicy
import androidx.work.NetworkType
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.OneTimeWorkRequest
import androidx.work.WorkInfo
import androidx.work.WorkManager
import androidx.work.workDataOf
import com.kltn.travelassistant.feature.downloads.domain.PackageCity
import com.kltn.travelassistant.feature.downloads.domain.PackageSyncFailureCode
import com.kltn.travelassistant.feature.downloads.domain.PackageSyncPhase
import com.kltn.travelassistant.feature.downloads.domain.PackageWorkState
import dagger.hilt.android.qualifiers.ApplicationContext
import java.util.concurrent.TimeUnit
import javax.inject.Inject
import javax.inject.Singleton
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map

interface PackageWorkScheduler {
    fun observe(city: PackageCity): Flow<PackageWorkState>

    fun enqueue(city: PackageCity, replace: Boolean)
}

@Singleton
class WorkManagerPackageScheduler @Inject constructor(
    @ApplicationContext context: Context,
    private val requestFactory: PackageWorkRequestFactory,
) : PackageWorkScheduler {
    private val workManager = WorkManager.getInstance(context)

    override fun observe(city: PackageCity): Flow<PackageWorkState> =
        workManager.getWorkInfosForUniqueWorkFlow(uniqueWorkName(city))
            .map { workInfos ->
                (
                    workInfos.lastOrNull { !it.state.isFinished } ?:
                        workInfos.lastOrNull()
                    )?.toPackageWorkState() ?: PackageWorkState.Idle
            }

    override fun enqueue(city: PackageCity, replace: Boolean) {
        val request = requestFactory.create(city)
        workManager.enqueueUniqueWork(
            uniqueWorkName(city),
            if (replace) ExistingWorkPolicy.REPLACE else ExistingWorkPolicy.KEEP,
            request,
        )
    }

    private fun WorkInfo.toPackageWorkState(): PackageWorkState = when (state) {
        WorkInfo.State.ENQUEUED,
        WorkInfo.State.BLOCKED -> if (runAttemptCount > 0) {
            PackageWorkState.Failed(PackageSyncFailureCode.NETWORK_UNAVAILABLE)
        } else {
            PackageWorkState.Running(PackageSyncPhase.QUEUED)
        }
        WorkInfo.State.RUNNING -> PackageWorkState.Running(
            progress.getString(PackageSyncWorker.KEY_PHASE)
                ?.let { value ->
                    PackageSyncPhase.entries.firstOrNull { it.name == value }
                }
                ?: PackageSyncPhase.DOWNLOADING_MANIFEST,
        )
        WorkInfo.State.SUCCEEDED -> PackageWorkState.Succeeded
        WorkInfo.State.FAILED -> PackageWorkState.Failed(
            outputData.getString(PackageSyncWorker.KEY_FAILURE_CODE)
                ?.let(::mapFailure)
                ?: PackageSyncFailureCode.INVALID_DATA,
        )
        WorkInfo.State.CANCELLED -> PackageWorkState.Failed(
            PackageSyncFailureCode.CANCELLED,
        )
    }

    private fun mapFailure(value: String): PackageSyncFailureCode = when (
        PackageSyncError.entries.firstOrNull { it.name == value }
    ) {
        PackageSyncError.NETWORK_UNAVAILABLE ->
            PackageSyncFailureCode.NETWORK_UNAVAILABLE
        PackageSyncError.TEMPORARY_SERVER_FAILURE ->
            PackageSyncFailureCode.TEMPORARY_SERVER_FAILURE
        PackageSyncError.INVALID_MANIFEST ->
            PackageSyncFailureCode.INVALID_MANIFEST
        PackageSyncError.UNSUPPORTED_PACKAGE ->
            PackageSyncFailureCode.UNSUPPORTED_PACKAGE
        PackageSyncError.CHECKSUM_MISMATCH ->
            PackageSyncFailureCode.CHECKSUM_MISMATCH
        PackageSyncError.INVALID_DATA ->
            PackageSyncFailureCode.INVALID_DATA
        PackageSyncError.ACTIVATION_FAILED ->
            PackageSyncFailureCode.ACTIVATION_FAILED
        null -> PackageSyncFailureCode.INVALID_DATA
    }

    companion object {
        fun uniqueWorkName(city: PackageCity): String = "travel-package-sync-${city.code}"

        fun workTag(city: PackageCity): String = "travel-package-${city.code}"
    }
}

class PackageWorkRequestFactory @Inject constructor() {
    fun create(city: PackageCity): OneTimeWorkRequest {
        val constraints = Constraints.Builder()
            .setRequiredNetworkType(NetworkType.CONNECTED)
            .build()
        return OneTimeWorkRequestBuilder<PackageSyncWorker>()
            .setInputData(workDataOf(PackageSyncWorker.KEY_CITY_CODE to city.code))
            .setConstraints(constraints)
            .setBackoffCriteria(
                BackoffPolicy.EXPONENTIAL,
                INITIAL_BACKOFF_SECONDS,
                TimeUnit.SECONDS,
            )
            .addTag(WorkManagerPackageScheduler.workTag(city))
            .build()
    }

    companion object {
        const val INITIAL_BACKOFF_SECONDS = 30L
    }
}
