package com.kltn.travelassistant.feature.home.presentation

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.kltn.travelassistant.analytics.GeocontextResultState
import com.kltn.travelassistant.analytics.NoOpProductAnalytics
import com.kltn.travelassistant.analytics.ProductAnalytics
import com.kltn.travelassistant.analytics.ProductAnalyticsEvent
import com.kltn.travelassistant.analytics.trackSafely
import com.kltn.travelassistant.data.location.LocationAcquisitionResult
import com.kltn.travelassistant.data.location.LocationClient
import com.kltn.travelassistant.data.repository.AppInfoRepository
import com.kltn.travelassistant.feature.home.domain.DemoLocationPresetProvider
import com.kltn.travelassistant.feature.nearby.domain.NearbySearchRepository
import com.kltn.travelassistant.feature.nearby.domain.NearbySearchResult
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
    private val nearbySearchRepository: NearbySearchRepository,
    private val demoLocationPresetProvider: DemoLocationPresetProvider,
    private val productAnalytics: ProductAnalytics = NoOpProductAnalytics,
) : ViewModel() {
    private val mutableUiState = MutableStateFlow(
        HomeUiState(
            appName = repository.appName.value,
            demoLocationPresets = demoLocationPresetProvider.presets.map { preset ->
                DemoLocationPresetUiModel(id = preset.id, label = preset.label)
            },
        ),
    )
    val uiState: StateFlow<HomeUiState> = mutableUiState.asStateFlow()

    private var locationRequestJob: Job? = null
    private var locationActionGeneration = 0L
    private var nearbySearchJob: Job? = null
    private var nearbySearchGeneration = 0L
    private var pendingGeocontextOpen = false
    private var geocontextOpenRecorded = false

    init {
        viewModelScope.launch {
            repository.appName.collect { appName ->
                mutableUiState.update { state -> state.copy(appName = appName) }
            }
        }
    }

    fun onLocationPermissionRequestStarted(): Long? {
        if (
            locationRequestJob?.isActive == true ||
            mutableUiState.value.locationState == LocationUiState.Loading
        ) {
            return null
        }
        return beginRealLocationAction()
    }

    fun onLocationPermissionGranted(actionId: Long? = null) {
        if (locationRequestJob?.isActive == true) return

        val activeActionId = when {
            actionId != null -> {
                if (actionId != locationActionGeneration) return
                actionId
            }
            mutableUiState.value.locationState == LocationUiState.Loading ->
                locationActionGeneration
            else -> beginRealLocationAction()
        }
        updateLocationState(LocationUiState.Loading)
        locationRequestJob = viewModelScope.launch {
            val result = try {
                locationClient.getCurrentLocation()
            } catch (exception: CancellationException) {
                throw exception
            } catch (_: Exception) {
                LocationAcquisitionResult.Failure
            }
            if (activeActionId != locationActionGeneration) return@launch
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
            locationRequestJob = null
            if (state is LocationUiState.Available) {
                if (!geocontextOpenRecorded) pendingGeocontextOpen = true
                runNearbySearch(
                    latitude = state.location.latitude,
                    longitude = state.location.longitude,
                    locationActionId = activeActionId,
                )
            }
        }
    }

    fun onLocationPermissionDenied(
        canRequestPermissionAgain: Boolean,
        actionId: Long? = null,
    ) {
        if (locationRequestJob?.isActive == true) return
        if (actionId != null && actionId != locationActionGeneration) return
        if (actionId == null && mutableUiState.value.locationState != LocationUiState.Loading) {
            beginRealLocationAction()
        }
        updateLocationState(
            LocationUiState.PermissionDenied(
                canRequestPermissionAgain = canRequestPermissionAgain,
            ),
        )
    }

    fun onLocationRequestCancelled() {
        pendingGeocontextOpen = false
        val activeRequest = locationRequestJob?.takeIf { job -> job.isActive }
        val isWaitingForPermission = mutableUiState.value.locationState == LocationUiState.Loading
        if (activeRequest == null && !isWaitingForPermission) return
        locationActionGeneration += 1
        activeRequest?.cancel()
        locationRequestJob = null
        cancelNearbySearch()
        updateLocationState(LocationUiState.Error(LocationError.CANCELLED))
    }

    fun onDemoLocationPresetSelected(presetId: String) {
        val preset = demoLocationPresetProvider.findById(presetId) ?: return
        val actionId = beginLocationAction(selectedDemoLocationPresetId = preset.id)
        updateLocationState(LocationUiState.Available(preset.location))
        runNearbySearch(
            latitude = preset.location.latitude,
            longitude = preset.location.longitude,
            locationActionId = actionId,
        )
    }

    fun onNearbyQueryChanged(query: String) {
        if (query == mutableUiState.value.nearbyQuery) return
        mutableUiState.update { state -> state.copy(nearbyQuery = query) }
        val location = (mutableUiState.value.locationState as? LocationUiState.Available)
            ?.location
            ?: return
        runNearbySearch(
            latitude = location.latitude,
            longitude = location.longitude,
            locationActionId = locationActionGeneration,
        )
    }

    private fun runNearbySearch(
        latitude: Double,
        longitude: Double,
        locationActionId: Long,
    ) {
        nearbySearchJob?.cancel()
        val generation = ++nearbySearchGeneration
        val query = mutableUiState.value.nearbyQuery
        updateNearbySearchState(NearbySearchUiState.Loading)
        nearbySearchJob = viewModelScope.launch {
            val result = try {
                nearbySearchRepository.search(
                    latitude = latitude,
                    longitude = longitude,
                    query = query,
                )
            } catch (exception: CancellationException) {
                throw exception
            } catch (_: Exception) {
                NearbySearchResult.DatabaseError
            }
            if (
                generation != nearbySearchGeneration ||
                locationActionId != locationActionGeneration
            ) {
                return@launch
            }
            val searchState = when (result) {
                is NearbySearchResult.Success -> if (result.pois.isEmpty()) {
                    NearbySearchUiState.Empty
                } else {
                    NearbySearchUiState.Content(result.pois.toList())
                }
                NearbySearchResult.InvalidLocation,
                NearbySearchResult.DatabaseError,
                -> NearbySearchUiState.Error
            }
            updateNearbySearchState(searchState)
            if (pendingGeocontextOpen) {
                val analyticsState = when (searchState) {
                    is NearbySearchUiState.Content -> GeocontextResultState.CONTENT
                    NearbySearchUiState.Empty -> GeocontextResultState.EMPTY
                    NearbySearchUiState.WaitingForLocation,
                    NearbySearchUiState.Loading,
                    NearbySearchUiState.Error,
                    -> null
                }
                analyticsState?.let { resultState ->
                    productAnalytics.trackSafely(
                        ProductAnalyticsEvent.GeocontextOpened(resultState),
                    )
                    pendingGeocontextOpen = false
                    geocontextOpenRecorded = true
                }
            }
        }
    }

    private fun beginRealLocationAction(): Long {
        val actionId = beginLocationAction(selectedDemoLocationPresetId = null)
        updateLocationState(LocationUiState.Loading)
        return actionId
    }

    private fun beginLocationAction(selectedDemoLocationPresetId: String?): Long {
        locationActionGeneration += 1
        locationRequestJob?.cancel()
        locationRequestJob = null
        cancelNearbySearch()
        pendingGeocontextOpen = false
        mutableUiState.update { state ->
            state.copy(selectedDemoLocationPresetId = selectedDemoLocationPresetId)
        }
        return locationActionGeneration
    }

    private fun cancelNearbySearch() {
        nearbySearchGeneration += 1
        nearbySearchJob?.cancel()
        nearbySearchJob = null
    }

    private fun updateLocationState(locationState: LocationUiState) {
        mutableUiState.update { state -> state.copy(locationState = locationState) }
    }

    private fun updateNearbySearchState(nearbySearchState: NearbySearchUiState) {
        mutableUiState.update { state -> state.copy(nearbySearchState = nearbySearchState) }
    }
}
