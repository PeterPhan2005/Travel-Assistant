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
import androidx.lifecycle.lifecycleScope
import com.kltn.travelassistant.data.auth.GoogleCredentialCoordinator
import com.kltn.travelassistant.feature.appshell.presentation.AppShellViewModel
import com.kltn.travelassistant.feature.auth.presentation.ProfileViewModel
import com.kltn.travelassistant.feature.auth.domain.GoogleSignInFailure
import com.kltn.travelassistant.feature.auth.domain.GoogleSignInResult
import com.kltn.travelassistant.feature.home.presentation.HomeViewModel
import com.kltn.travelassistant.feature.home.presentation.LocationUiState
import com.kltn.travelassistant.navigation.external.ExternalNavigationCoordinator
import dagger.hilt.android.AndroidEntryPoint
import javax.inject.Inject
import kotlinx.coroutines.launch
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.NonCancellable
import kotlinx.coroutines.withContext

@AndroidEntryPoint
class MainActivity : ComponentActivity() {
    @Inject
    lateinit var externalNavigationCoordinator: ExternalNavigationCoordinator

    @Inject
    lateinit var googleCredentialCoordinator: GoogleCredentialCoordinator

    private val appShellViewModel: AppShellViewModel by viewModels()
    private val homeViewModel: HomeViewModel by viewModels()
    private val profileViewModel: ProfileViewModel by viewModels()
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
                profileViewModel = profileViewModel,
                onUseCurrentLocation = ::onUseCurrentLocation,
                onOpenLocationSettings = ::openLocationSettings,
                onOpenExternalNavigation = externalNavigationCoordinator::open,
                onGoogleSignIn = ::onGoogleSignIn,
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

    private fun onGoogleSignIn() {
        val attemptId = profileViewModel.onGoogleSignInStarted() ?: return
        lifecycleScope.launch {
            try {
                val result = try {
                    googleCredentialCoordinator.signIn(this@MainActivity)
                } catch (exception: CancellationException) {
                    throw exception
                } catch (_: Exception) {
                    GoogleSignInResult.Failure(GoogleSignInFailure.UNKNOWN)
                }
                profileViewModel.onGoogleSignInResult(attemptId, result)
            } catch (exception: CancellationException) {
                withContext(NonCancellable) {
                    profileViewModel.onGoogleSignInResult(
                        attemptId,
                        GoogleSignInResult.Cancelled,
                    )
                }
                throw exception
            }
        }
    }

    private companion object {
        val FOREGROUND_LOCATION_PERMISSIONS = arrayOf(
            Manifest.permission.ACCESS_FINE_LOCATION,
            Manifest.permission.ACCESS_COARSE_LOCATION,
        )
    }
}
