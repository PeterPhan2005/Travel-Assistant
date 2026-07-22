package com.kltn.travelassistant.feature.home.presentation

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.tooling.preview.Preview
import com.kltn.travelassistant.R
import com.kltn.travelassistant.ui.theme.AppSpacing
import com.kltn.travelassistant.ui.theme.TravelAssistantTheme

@Composable
fun HomeScreen(
    uiState: HomeUiState,
    onUseCurrentLocation: () -> Unit,
    onOpenLocationSettings: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Column(
        modifier = modifier
            .fillMaxSize()
            .padding(AppSpacing.screen),
        verticalArrangement = Arrangement.spacedBy(AppSpacing.content),
    ) {
        Text(
            text = stringResource(R.string.destination_explore),
            modifier = Modifier.semantics { heading() },
            style = MaterialTheme.typography.headlineMedium,
        )
        Text(
            text = uiState.appName,
            style = MaterialTheme.typography.bodyLarge,
        )
        LocationContextSection(
            state = uiState.locationState,
            onUseCurrentLocation = onUseCurrentLocation,
            onOpenLocationSettings = onOpenLocationSettings,
        )
    }
}

@Composable
private fun LocationContextSection(
    state: LocationUiState,
    onUseCurrentLocation: () -> Unit,
    onOpenLocationSettings: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Column(
        modifier = modifier,
        verticalArrangement = Arrangement.spacedBy(AppSpacing.content),
    ) {
        Text(
            text = stringResource(R.string.location_section_title),
            style = MaterialTheme.typography.titleMedium,
        )
        when (state) {
            LocationUiState.Idle -> LocationActionButton(onClick = onUseCurrentLocation)
            LocationUiState.Loading -> {
                CircularProgressIndicator()
                Text(text = stringResource(R.string.location_loading))
            }
            is LocationUiState.Available -> {
                Text(text = stringResource(R.string.location_available_local_only))
                state.location.accuracyMeters?.let { accuracyMeters ->
                    Text(
                        text = stringResource(
                            R.string.location_accuracy,
                            accuracyMeters.toInt(),
                        ),
                        style = MaterialTheme.typography.bodySmall,
                    )
                }
                LocationActionButton(
                    text = stringResource(R.string.location_refresh),
                    onClick = onUseCurrentLocation,
                )
            }
            is LocationUiState.PermissionDenied -> {
                Text(text = stringResource(R.string.location_permission_denied))
                LocationActionButton(
                    text = stringResource(R.string.location_retry),
                    onClick = onUseCurrentLocation,
                )
                if (!state.canRequestPermissionAgain) {
                    OutlinedButton(onClick = onOpenLocationSettings) {
                        Text(text = stringResource(R.string.location_open_settings))
                    }
                }
            }
            is LocationUiState.Error -> {
                Text(text = stringResource(state.reason.messageRes))
                LocationActionButton(
                    text = stringResource(R.string.location_retry),
                    onClick = onUseCurrentLocation,
                )
            }
        }
    }
}

@Composable
private fun LocationActionButton(
    onClick: () -> Unit,
    text: String = stringResource(R.string.location_use_current),
) {
    Button(onClick = onClick) {
        Text(text = text)
    }
}

private val LocationError.messageRes: Int
    get() = when (this) {
        LocationError.PROVIDER_UNAVAILABLE -> R.string.location_provider_unavailable
        LocationError.TIMEOUT -> R.string.location_timeout
        LocationError.CANCELLED -> R.string.location_cancelled
        LocationError.FAILED -> R.string.location_error
    }

@Preview(showBackground = true)
@Composable
private fun HomeScreenPreview() {
    TravelAssistantTheme(dynamicColor = false) {
        HomeScreen(
            uiState = HomeUiState(appName = "Travel Assistant"),
            onUseCurrentLocation = {},
            onOpenLocationSettings = {},
        )
    }
}
