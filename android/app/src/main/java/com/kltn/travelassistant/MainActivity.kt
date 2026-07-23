package com.kltn.travelassistant

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Bundle
import android.provider.Settings
import androidx.activity.ComponentActivity
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.viewModels
import androidx.core.content.ContextCompat
import com.kltn.travelassistant.feature.appshell.presentation.AppShellViewModel
import com.kltn.travelassistant.feature.home.presentation.HomeViewModel
import com.kltn.travelassistant.feature.home.presentation.LocationUiState
import com.kltn.travelassistant.navigation.external.ExternalNavigationCoordinator
import dagger.hilt.android.AndroidEntryPoint
import javax.inject.Inject

@AndroidEntryPoint
class MainActivity : ComponentActivity() {
    @Inject
    lateinit var externalNavigationCoordinator: ExternalNavigationCoordinator

    private val appShellViewModel: AppShellViewModel by viewModels()
    private val homeViewModel: HomeViewModel by viewModels()
    private val locationPermissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions(),
    ) { permissions ->
        val hasForegroundPermission = permissions.getOrDefault(
            Manifest.permission.ACCESS_FINE_LOCATION,
            false,
        ) || permissions.getOrDefault(
            Manifest.permission.ACCESS_COARSE_LOCATION,
            false,
        ) || hasForegroundLocationPermission()

        if (hasForegroundPermission) {
            homeViewModel.onLocationPermissionGranted()
        } else {
            homeViewModel.onLocationPermissionDenied(
                canRequestPermissionAgain = shouldShowRequestPermissionRationale(
                    Manifest.permission.ACCESS_COARSE_LOCATION,
                ) || shouldShowRequestPermissionRationale(
                    Manifest.permission.ACCESS_FINE_LOCATION,
                ),
            )
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            TravelAssistantApp(
                appShellViewModel = appShellViewModel,
                homeViewModel = homeViewModel,
                onUseCurrentLocation = ::onUseCurrentLocation,
                onOpenLocationSettings = ::openLocationSettings,
                onOpenExternalNavigation = externalNavigationCoordinator::open,
            )
        }
    }

    override fun onStop() {
        homeViewModel.onLocationRequestCancelled()
        super.onStop()
    }

    private fun onUseCurrentLocation() {
        if (homeViewModel.uiState.value.locationState is LocationUiState.Loading) return

        if (hasForegroundLocationPermission()) {
            homeViewModel.onLocationPermissionGranted()
        } else {
            homeViewModel.onLocationPermissionRequestStarted()
            locationPermissionLauncher.launch(FOREGROUND_LOCATION_PERMISSIONS)
        }
    }

    private fun hasForegroundLocationPermission(): Boolean =
        ContextCompat.checkSelfPermission(
            this,
            Manifest.permission.ACCESS_COARSE_LOCATION,
        ) == PackageManager.PERMISSION_GRANTED || ContextCompat.checkSelfPermission(
            this,
            Manifest.permission.ACCESS_FINE_LOCATION,
        ) == PackageManager.PERMISSION_GRANTED

    private fun openLocationSettings() {
        startActivity(
            Intent(
                Settings.ACTION_APPLICATION_DETAILS_SETTINGS,
                Uri.fromParts("package", packageName, null),
            ),
        )
    }

    private companion object {
        val FOREGROUND_LOCATION_PERMISSIONS = arrayOf(
            Manifest.permission.ACCESS_FINE_LOCATION,
            Manifest.permission.ACCESS_COARSE_LOCATION,
        )
    }
}
