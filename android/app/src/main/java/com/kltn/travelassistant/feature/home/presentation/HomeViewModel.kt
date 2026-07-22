package com.kltn.travelassistant.feature.home.presentation

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.kltn.travelassistant.data.location.LocationAcquisitionResult
import com.kltn.travelassistant.data.location.LocationClient
import com.kltn.travelassistant.data.repository.AppInfoRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import javax.inject.Inject
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Job
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

@HiltViewModel
class HomeViewModel @Inject constructor(
    repository: AppInfoRepository,
    private val locationClient: LocationClient,
) : ViewModel() {
    private val mutableUiState = MutableStateFlow(
        HomeUiState(appName = repository.appName.value),
    )
    val uiState: StateFlow<HomeUiState> = mutableUiState.asStateFlow()

    private var locationRequestJob: Job? = null

    init {
        viewModelScope.launch {
            repository.appName.collect { appName ->
                mutableUiState.update { state -> state.copy(appName = appName) }
            }
        }
    }

    fun onLocationPermissionRequestStarted() {
        if (locationRequestJob?.isActive == true) return
        updateLocationState(LocationUiState.Loading)
    }

    fun onLocationPermissionGranted() {
        if (locationRequestJob?.isActive == true) return

        updateLocationState(LocationUiState.Loading)
        locationRequestJob = viewModelScope.launch {
            val result = try {
                locationClient.getCurrentLocation()
            } catch (exception: CancellationException) {
                throw exception
            } catch (_: Exception) {
                LocationAcquisitionResult.Failure
            }
            val state = when (result) {
                is LocationAcquisitionResult.Success -> LocationUiState.Available(result.location)
                LocationAcquisitionResult.PermissionDenied -> LocationUiState.PermissionDenied(
                    canRequestPermissionAgain = true,
                )
                LocationAcquisitionResult.ProviderUnavailable -> LocationUiState.Error(
                    LocationError.PROVIDER_UNAVAILABLE,
                )
                LocationAcquisitionResult.Timeout -> LocationUiState.Error(LocationError.TIMEOUT)
                LocationAcquisitionResult.Failure -> LocationUiState.Error(LocationError.FAILED)
            }
            updateLocationState(state)
        }
    }

    fun onLocationPermissionDenied(canRequestPermissionAgain: Boolean) {
        if (locationRequestJob?.isActive == true) return
        updateLocationState(
            LocationUiState.PermissionDenied(
                canRequestPermissionAgain = canRequestPermissionAgain,
            ),
        )
    }

    fun onLocationRequestCancelled() {
        val activeRequest = locationRequestJob?.takeIf { job -> job.isActive } ?: return
        activeRequest.cancel()
        locationRequestJob = null
        updateLocationState(LocationUiState.Error(LocationError.CANCELLED))
    }

    private fun updateLocationState(locationState: LocationUiState) {
        mutableUiState.update { state -> state.copy(locationState = locationState) }
    }
}
