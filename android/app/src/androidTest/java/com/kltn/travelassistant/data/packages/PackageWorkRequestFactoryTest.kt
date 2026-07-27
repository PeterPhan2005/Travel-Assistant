package com.kltn.travelassistant.data.packages

import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.work.BackoffPolicy
import androidx.work.NetworkType
import com.kltn.travelassistant.feature.downloads.domain.PackageCity
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class PackageWorkRequestFactoryTest {
    @Test
    fun requestIsUniquePerCityNetworkConstrainedAndContainsOnlySafeInput() {
        val request = PackageWorkRequestFactory().create(PackageCity.HCMC)

        assertEquals(
            "travel-package-sync-hcmc",
            WorkManagerPackageScheduler.uniqueWorkName(PackageCity.HCMC),
        )
        assertTrue(request.tags.contains("travel-package-hcmc"))
        assertEquals(
            "hcmc",
            request.workSpec.input.getString(PackageSyncWorker.KEY_CITY_CODE),
        )
        assertEquals(setOf(PackageSyncWorker.KEY_CITY_CODE), request.workSpec.input.keyValueMap.keys)
        assertEquals(
            NetworkType.CONNECTED,
            request.workSpec.constraints.requiredNetworkType,
        )
        assertEquals(BackoffPolicy.EXPONENTIAL, request.workSpec.backoffPolicy)
        assertEquals(
            PackageWorkRequestFactory.INITIAL_BACKOFF_SECONDS * 1_000,
            request.workSpec.backoffDelayDuration,
        )
    }

    @Test
    fun progressAndFailureDataContainNoBodiesUrlsOrCredentials() {
        val progress = PackageSyncWorker.progressData(
            com.kltn.travelassistant.feature.downloads.domain.PackageSyncPhase.VERIFYING,
        )
        val failure = PackageSyncWorker.failureData(PackageSyncError.CHECKSUM_MISMATCH)

        assertEquals(setOf(PackageSyncWorker.KEY_PHASE), progress.keyValueMap.keys)
        assertEquals(setOf(PackageSyncWorker.KEY_FAILURE_CODE), failure.keyValueMap.keys)
        val combined = (progress.keyValueMap.values + failure.keyValueMap.values)
            .joinToString(" ")
            .lowercase()
        assertFalse(combined.contains("http"))
        assertFalse(combined.contains("token"))
        assertFalse(combined.contains("authorization"))
        assertFalse(combined.contains("{"))
    }
}
