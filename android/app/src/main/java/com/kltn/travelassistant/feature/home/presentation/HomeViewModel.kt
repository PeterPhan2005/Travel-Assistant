package com.kltn.travelassistant.feature.home.presentation

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.kltn.travelassistant.data.repository.AppInfoRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import javax.inject.Inject
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.flow.stateIn

@HiltViewModel
class HomeViewModel @Inject constructor(
    repository: AppInfoRepository,
) : ViewModel() {
    val uiState: StateFlow<HomeUiState> = repository.appName
        .map { appName -> HomeUiState(appName = appName) }
        .stateIn(
            scope = viewModelScope,
            started = SharingStarted.Eagerly,
            initialValue = HomeUiState(appName = repository.appName.value),
        )
}
