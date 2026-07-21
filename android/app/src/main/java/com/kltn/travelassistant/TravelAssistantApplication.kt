package com.kltn.travelassistant

import android.app.Application
import android.util.Log
import com.kltn.travelassistant.data.seed.SeedImportResult
import com.kltn.travelassistant.data.seed.SeedStartupCoordinator
import dagger.hilt.android.HiltAndroidApp
import javax.inject.Inject
import kotlinx.coroutines.CoroutineExceptionHandler
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.launch

@HiltAndroidApp
class TravelAssistantApplication : Application() {
    @Inject
    lateinit var seedStartupCoordinator: SeedStartupCoordinator

    private val seedFailureHandler = CoroutineExceptionHandler { _, _ ->
        Log.w(TAG, "Bundled seed initialization failed")
    }
    private val applicationScope = CoroutineScope(
        SupervisorJob() + Dispatchers.Default + seedFailureHandler,
    )

    override fun onCreate() {
        super.onCreate()
        applicationScope.launch {
            when (val result = seedStartupCoordinator.initialize()) {
                is SeedImportResult.Imported -> Log.i(
                    TAG,
                    "Bundled seed imported (${result.counts.pois} POIs)",
                )
                SeedImportResult.AlreadyImported -> Log.i(TAG, "Bundled seed already imported")
                is SeedImportResult.Failed -> Log.w(
                    TAG,
                    "Bundled seed import failed (${result.reason.name.lowercase()})",
                )
            }
        }
    }

    companion object {
        private const val TAG = "TravelAssistantSeed"
    }
}
