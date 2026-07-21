package com.kltn.travelassistant

import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Scaffold
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.kltn.travelassistant.feature.home.presentation.HomeScreen
import com.kltn.travelassistant.feature.home.presentation.HomeViewModel

@Composable
fun TravelAssistantApp(
    homeViewModel: HomeViewModel,
    modifier: Modifier = Modifier,
) {
    val uiState by homeViewModel.uiState.collectAsStateWithLifecycle()

    Scaffold(modifier = modifier.fillMaxSize()) { innerPadding ->
        HomeScreen(
            uiState = uiState,
            modifier = Modifier.padding(innerPadding),
        )
    }
}
