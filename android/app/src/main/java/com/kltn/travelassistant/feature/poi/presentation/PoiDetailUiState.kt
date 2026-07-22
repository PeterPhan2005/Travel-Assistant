package com.kltn.travelassistant.feature.poi.presentation

import com.kltn.travelassistant.feature.poi.domain.PoiDetail

sealed interface PoiDetailUiState {
    data object Loading : PoiDetailUiState

    data class Content(val detail: PoiDetail) : PoiDetailUiState

    data object NotFound : PoiDetailUiState

    data object Error : PoiDetailUiState
}
