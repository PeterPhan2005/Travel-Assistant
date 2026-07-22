package com.kltn.travelassistant.feature.home.presentation

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.clickable
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.tooling.preview.Preview
import com.kltn.travelassistant.R
import com.kltn.travelassistant.feature.nearby.domain.NearbyPoi
import com.kltn.travelassistant.feature.nearby.presentation.DistanceFormatter
import com.kltn.travelassistant.feature.nearby.presentation.labelRes
import com.kltn.travelassistant.ui.theme.AppSpacing
import com.kltn.travelassistant.ui.theme.TravelAssistantTheme

@Composable
fun HomeScreen(
    uiState: HomeUiState,
    onUseCurrentLocation: () -> Unit,
    onOpenLocationSettings: () -> Unit,
    onNearbyQueryChanged: (String) -> Unit,
    onPoiSelected: (String) -> Unit,
    modifier: Modifier = Modifier,
) {
    LazyColumn(
        modifier = modifier
            .fillMaxSize(),
        contentPadding = androidx.compose.foundation.layout.PaddingValues(AppSpacing.screen),
        verticalArrangement = Arrangement.spacedBy(AppSpacing.content),
    ) {
        item {
            Text(
                text = stringResource(R.string.destination_explore),
                modifier = Modifier.semantics { heading() },
                style = MaterialTheme.typography.headlineMedium,
            )
        }
        item {
            Text(
                text = uiState.appName,
                style = MaterialTheme.typography.bodyLarge,
            )
        }
        item {
            LocationContextSection(
                state = uiState.locationState,
                onUseCurrentLocation = onUseCurrentLocation,
                onOpenLocationSettings = onOpenLocationSettings,
            )
        }
        item {
            Text(
                text = stringResource(R.string.nearby_section_title),
                modifier = Modifier.semantics { heading() },
                style = MaterialTheme.typography.titleMedium,
            )
        }
        if (uiState.locationState !is LocationUiState.Available) {
            item {
                Text(text = stringResource(R.string.nearby_location_required))
            }
        } else {
            item {
                OutlinedTextField(
                    value = uiState.nearbyQuery,
                    onValueChange = onNearbyQueryChanged,
                    modifier = Modifier.fillMaxWidth(),
                    label = { Text(text = stringResource(R.string.nearby_search_label)) },
                    placeholder = {
                        Text(text = stringResource(R.string.nearby_search_placeholder))
                    },
                    singleLine = true,
                )
            }
            item {
                Text(
                    text = stringResource(R.string.nearby_straight_line_notice),
                    style = MaterialTheme.typography.bodySmall,
                )
            }
            when (val nearbyState = uiState.nearbySearchState) {
                NearbySearchUiState.WaitingForLocation -> item {
                    Text(text = stringResource(R.string.nearby_location_required))
                }
                NearbySearchUiState.Loading -> item {
                    Column(verticalArrangement = Arrangement.spacedBy(AppSpacing.content)) {
                        CircularProgressIndicator()
                        Text(text = stringResource(R.string.nearby_loading))
                    }
                }
                is NearbySearchUiState.Content -> items(
                    items = nearbyState.results,
                    key = NearbyPoi::poiId,
                ) { poi ->
                    NearbyPoiRow(
                        poi = poi,
                        onClick = { onPoiSelected(poi.poiId) },
                    )
                }
                NearbySearchUiState.Empty -> item {
                    Text(text = stringResource(R.string.nearby_empty))
                }
                NearbySearchUiState.Error -> item {
                    Text(text = stringResource(R.string.nearby_error))
                }
            }
        }
    }
}

@Composable
private fun NearbyPoiRow(
    poi: NearbyPoi,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Column(
        modifier = modifier
            .fillMaxWidth()
            .clickable(onClick = onClick)
            .semantics(mergeDescendants = true) {},
        verticalArrangement = Arrangement.spacedBy(AppSpacing.content / 2),
    ) {
        Text(
            text = poi.displayName,
            style = MaterialTheme.typography.titleSmall,
        )
        Text(
            text = stringResource(poi.categoryLabel.labelRes),
            style = MaterialTheme.typography.bodyMedium,
        )
        Text(
            text = stringResource(
                R.string.nearby_distance_km,
                DistanceFormatter.formatKilometresValue(poi.distanceMeters),
            ),
            style = MaterialTheme.typography.bodyMedium,
        )
        HorizontalDivider()
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
            onNearbyQueryChanged = {},
            onPoiSelected = {},
        )
    }
}
