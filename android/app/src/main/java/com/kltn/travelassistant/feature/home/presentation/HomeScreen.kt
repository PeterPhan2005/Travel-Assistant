package com.kltn.travelassistant.feature.home.presentation

import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.tooling.preview.Preview
import com.kltn.travelassistant.ui.theme.TravelAssistantTheme

@Composable
fun HomeScreen(
    uiState: HomeUiState,
    modifier: Modifier = Modifier,
) {
    Text(
        text = uiState.appName,
        modifier = modifier,
    )
}

@Preview(showBackground = true)
@Composable
private fun HomeScreenPreview() {
    TravelAssistantTheme {
        HomeScreen(uiState = HomeUiState(appName = "Travel Assistant"))
    }
}
