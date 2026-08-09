package com.kltn.travelassistant.feature.poi.presentation

import androidx.lifecycle.SavedStateHandle
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.kltn.travelassistant.analytics.NavigationConversionStage
import com.kltn.travelassistant.analytics.NoOpProductAnalytics
import com.kltn.travelassistant.analytics.ProductAnalytics
import com.kltn.travelassistant.analytics.trackNavigationConversionSafely
import com.kltn.travelassistant.feature.poi.domain.PoiDetailRepository
import com.kltn.travelassistant.feature.poi.domain.PoiDetailResult
import com.kltn.travelassistant.navigation.PoiDetailDestination
import dagger.hilt.android.lifecycle.HiltViewModel
import javax.inject.Inject
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Job
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

@HiltViewModel
class PoiDetailViewModel @Inject constructor(
    savedStateHandle: SavedStateHandle,
    private val repository: PoiDetailRepository,
    private val productAnalytics: ProductAnalytics = NoOpProductAnalytics,
) : ViewModel() {
    private val poiId = savedStateHandle.get<String>(PoiDetailDestination.POI_ID_ARGUMENT)
        .orEmpty()
    private val mutableUiState = MutableStateFlow<PoiDetailUiState>(PoiDetailUiState.Loading)
    val uiState: StateFlow<PoiDetailUiState> = mutableUiState.asStateFlow()
    private var loadJob: Job? = null
    private var detailOpenRecorded = false

    init {
        load()
    }

    fun retry() {
        if (mutableUiState.value != PoiDetailUiState.Error || loadJob?.isActive == true) return
        load()
    }

    private fun load() {
        mutableUiState.value = PoiDetailUiState.Loading
        loadJob = viewModelScope.launch {
            if (poiId.isBlank()) {
                mutableUiState.value = PoiDetailUiState.NotFound
                return@launch
            }
            val result = try {
                repository.getPoiDetail(poiId, VIETNAMESE_LANGUAGE_CODE)
            } catch (exception: CancellationException) {
                throw exception
            } catch (_: Exception) {
                PoiDetailResult.DatabaseError
            }
            mutableUiState.value = when (result) {
                is PoiDetailResult.Success -> {
                    if (!detailOpenRecorded) {
                        productAnalytics.trackNavigationConversionSafely(
                            stage = NavigationConversionStage.DETAIL_OPENED,
                            poiId = result.detail.poiId,
                        )
                        detailOpenRecorded = true
                    }
                    PoiDetailUiState.Content(result.detail)
                }
                PoiDetailResult.NotFound -> PoiDetailUiState.NotFound
                PoiDetailResult.DatabaseError -> PoiDetailUiState.Error
            }
        }
    }

    private companion object {
        const val VIETNAMESE_LANGUAGE_CODE = "vi"
    }
}
