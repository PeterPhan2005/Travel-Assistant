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
import com.kltn.travelassistant.feature.assistant.presentation.AssistantViewModel
import com.kltn.travelassistant.feature.auth.domain.GoogleSignInFailure
import com.kltn.travelassistant.feature.auth.domain.GoogleSignInResult
import com.kltn.travelassistant.feature.auth.presentation.ProfileViewModel
import com.kltn.travelassistant.feature.downloads.presentation.DownloadsViewModel
import com.kltn.travelassistant.feature.home.presentation.HomeViewModel
import com.kltn.travelassistant.feature.home.presentation.LocationUiState
import com.kltn.travelassistant.feature.itinerary.presentation.ItineraryViewModel
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
    private val assistantViewModel: AssistantViewModel by viewModels()
    private val homeViewModel: HomeViewModel by viewModels()
    private val itineraryViewModel: ItineraryViewModel by viewModels()
    private val profileViewModel: ProfileViewModel by viewModels()
    private val downloadsViewModel: DownloadsViewModel by viewModels()
    private var pendingMicrophonePermissionAttemptId: Long? = null
    private var isMicrophonePermissionResultOutstanding = false
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
    private val microphonePermissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestPermission(),
    ) { granted ->
        isMicrophonePermissionResultOutstanding = false
        val attemptId = pendingMicrophonePermissionAttemptId ?: return@registerForActivityResult
        pendingMicrophonePermissionAttemptId = null
        if (granted || hasMicrophonePermission()) {
            assistantViewModel.onMicrophonePermissionGranted(attemptId)
        } else {
            assistantViewModel.onMicrophonePermissionDenied(
                attemptId = attemptId,
                canRequestPermissionAgain = shouldShowRequestPermissionRationale(
                    Manifest.permission.RECORD_AUDIO,
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
                assistantViewModel = assistantViewModel,
                homeViewModel = homeViewModel,
                itineraryViewModel = itineraryViewModel,
                profileViewModel = profileViewModel,
                downloadsViewModel = downloadsViewModel,
                onUseCurrentLocation = ::onUseCurrentLocation,
                onOpenLocationSettings = ::openApplicationSettings,
                onVoiceInput = ::onVoiceInput,
                onCancelVoiceInput = ::onCancelVoiceInput,
                onAssistantScreenLeft = ::onAssistantScreenLeft,
                onOpenMicrophoneSettings = ::openApplicationSettings,
                onOpenExternalNavigation = externalNavigationCoordinator::open,
                onGoogleSignIn = ::onGoogleSignIn,
            )
        }
    }

    override fun onResume() {
        super.onResume()
        assistantViewModel.onMicrophonePermissionStatusRefreshed(
            isGranted = hasMicrophonePermission(),
        )
    }

    override fun onStop() {
        onAssistantScreenLeft()
        itineraryViewModel.onAppBackgrounded()
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

    private fun onVoiceInput() {
        if (
            pendingMicrophonePermissionAttemptId != null ||
            isMicrophonePermissionResultOutstanding
        ) {
            return
        }
        val attemptId = assistantViewModel.beginVoiceInputAttempt() ?: return

        if (hasMicrophonePermission()) {
            assistantViewModel.onMicrophonePermissionGranted(attemptId)
        } else {
            pendingMicrophonePermissionAttemptId = attemptId
            isMicrophonePermissionResultOutstanding = true
            assistantViewModel.onMicrophonePermissionRequestStarted(attemptId)
            microphonePermissionLauncher.launch(Manifest.permission.RECORD_AUDIO)
        }
    }

    private fun onCancelVoiceInput() {
        pendingMicrophonePermissionAttemptId = null
        assistantViewModel.cancelSpeechRecognition()
    }

    private fun onAssistantScreenLeft() {
        pendingMicrophonePermissionAttemptId = null
        assistantViewModel.onAssistantScreenLeft()
    }

    private fun hasMicrophonePermission(): Boolean =
        ContextCompat.checkSelfPermission(
            this,
            Manifest.permission.RECORD_AUDIO,
        ) == PackageManager.PERMISSION_GRANTED

    private fun openApplicationSettings() {
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
