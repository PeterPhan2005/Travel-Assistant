package com.kltn.travelassistant.data.preferences

import android.content.Context
import androidx.work.BackoffPolicy
import androidx.work.Constraints
import androidx.work.ExistingWorkPolicy
import androidx.work.NetworkType
import androidx.work.OneTimeWorkRequest
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.WorkInfo
import androidx.work.WorkManager
import dagger.hilt.android.qualifiers.ApplicationContext
import java.util.concurrent.TimeUnit
import javax.inject.Inject
import javax.inject.Singleton
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map

internal sealed interface PreferenceWorkState {
    data object Idle : PreferenceWorkState

    data object Running : PreferenceWorkState

    data object Succeeded : PreferenceWorkState

    data object RetryableFailure : PreferenceWorkState

    data object AuthenticationFailure : PreferenceWorkState

    data object InvalidDocument : PreferenceWorkState
}

internal interface PreferenceWorkScheduler {
    fun observe(): Flow<PreferenceWorkState>

    fun enqueue()
}

@Singleton
internal class WorkManagerPreferenceScheduler @Inject constructor(
    @ApplicationContext context: Context,
    private val requestFactory: PreferenceWorkRequestFactory,
) : PreferenceWorkScheduler {
    private val workManager = WorkManager.getInstance(context)

    override fun observe(): Flow<PreferenceWorkState> =
        workManager.getWorkInfosForUniqueWorkFlow(UNIQUE_WORK_NAME)
            .map { workInfos ->
                (
                    workInfos.lastOrNull { !it.state.isFinished }
                        ?: workInfos.lastOrNull()
                    )?.toPreferenceWorkState() ?: PreferenceWorkState.Idle
            }

    override fun enqueue() {
        workManager.enqueueUniqueWork(
            UNIQUE_WORK_NAME,
            ExistingWorkPolicy.KEEP,
            requestFactory.create(),
        )
    }

    private fun WorkInfo.toPreferenceWorkState(): PreferenceWorkState = when (state) {
        WorkInfo.State.ENQUEUED,
        WorkInfo.State.BLOCKED,
        WorkInfo.State.RUNNING,
        -> if (runAttemptCount > 0 && state != WorkInfo.State.RUNNING) {
            PreferenceWorkState.RetryableFailure
        } else {
            PreferenceWorkState.Running
        }
        WorkInfo.State.SUCCEEDED -> PreferenceWorkState.Succeeded
        WorkInfo.State.FAILED -> when (
            outputData.getString(PreferenceSyncWorker.KEY_FAILURE_CODE)
                ?.let { code ->
                    PreferenceSyncOutcome.entries.firstOrNull { it.name == code }
                }
        ) {
            PreferenceSyncOutcome.AUTHENTICATION_FAILURE ->
                PreferenceWorkState.AuthenticationFailure
            PreferenceSyncOutcome.INVALID_DOCUMENT ->
                PreferenceWorkState.InvalidDocument
            else -> PreferenceWorkState.InvalidDocument
        }
        WorkInfo.State.CANCELLED -> PreferenceWorkState.RetryableFailure
    }

    companion object {
        const val UNIQUE_WORK_NAME = "preference-sync"
        const val WORK_TAG = "preference-sync"
    }
}

internal class PreferenceWorkRequestFactory @Inject constructor() {
    fun create(): OneTimeWorkRequest = OneTimeWorkRequestBuilder<PreferenceSyncWorker>()
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
        .addTag(WorkManagerPreferenceScheduler.WORK_TAG)
        .build()

    companion object {
        const val INITIAL_BACKOFF_SECONDS = 30L
    }
}

