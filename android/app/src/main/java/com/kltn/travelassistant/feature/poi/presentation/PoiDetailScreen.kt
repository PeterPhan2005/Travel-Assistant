package com.kltn.travelassistant.feature.poi.presentation

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.semantics
import androidx.hilt.lifecycle.viewmodel.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.kltn.travelassistant.R
import com.kltn.travelassistant.feature.nearby.presentation.labelRes
import com.kltn.travelassistant.feature.poi.domain.PoiDetail
import com.kltn.travelassistant.feature.poi.domain.PoiMenuItem
import com.kltn.travelassistant.feature.poi.domain.PoiNavigationTarget
import com.kltn.travelassistant.navigation.external.ExternalNavigationResult
import com.kltn.travelassistant.ui.theme.AppSpacing

@Composable
fun PoiDetailRoute(
    onBack: () -> Unit,
    onOpenExternalNavigation: (PoiNavigationTarget) -> ExternalNavigationResult,
    modifier: Modifier = Modifier,
    viewModel: PoiDetailViewModel = hiltViewModel(),
) {
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()
    var navigationError by remember { mutableStateOf<PoiNavigationError?>(null) }
    PoiDetailScreen(
        uiState = uiState,
        onBack = onBack,
        onRetry = viewModel::retry,
        navigationError = navigationError,
        onNavigate = { target ->
            navigationError = null
            navigationError = onOpenExternalNavigation(target).toPoiNavigationError()
        },
        modifier = modifier,
    )
}

@Composable
fun PoiDetailScreen(
    uiState: PoiDetailUiState,
    onBack: () -> Unit,
    onRetry: () -> Unit,
    modifier: Modifier = Modifier,
    navigationError: PoiNavigationError? = null,
    onNavigate: (PoiNavigationTarget) -> Unit = {},
) {
    Column(modifier = modifier.fillMaxSize()) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = AppSpacing.content),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            IconButton(onClick = onBack) {
                Icon(
                    imageVector = Icons.AutoMirrored.Filled.ArrowBack,
                    contentDescription = stringResource(R.string.poi_detail_back),
                )
            }
            Text(
                text = stringResource(R.string.poi_detail_title),
                style = MaterialTheme.typography.titleLarge,
            )
        }
        when (uiState) {
            PoiDetailUiState.Loading -> DetailMessage(
                text = stringResource(R.string.poi_detail_loading),
                showProgress = true,
            )
            PoiDetailUiState.NotFound -> DetailMessage(
                text = stringResource(R.string.poi_detail_not_found),
            )
            PoiDetailUiState.Error -> DetailMessage(
                text = stringResource(R.string.poi_detail_error),
                action = {
                    Button(onClick = onRetry) {
                        Text(text = stringResource(R.string.poi_detail_retry))
                    }
                },
            )
            is PoiDetailUiState.Content -> PoiDetailContent(
                detail = uiState.detail,
                navigationError = navigationError,
                onNavigate = onNavigate,
            )
        }
    }
}

@Composable
private fun DetailMessage(
    text: String,
    showProgress: Boolean = false,
    action: (@Composable () -> Unit)? = null,
) {
    Column(
        modifier = Modifier.padding(AppSpacing.screen),
        verticalArrangement = Arrangement.spacedBy(AppSpacing.content),
    ) {
        if (showProgress) CircularProgressIndicator()
        Text(text = text)
        action?.invoke()
    }
}

@Composable
private fun PoiDetailContent(
    detail: PoiDetail,
    navigationError: PoiNavigationError?,
    onNavigate: (PoiNavigationTarget) -> Unit,
) {
    LazyColumn(
        contentPadding = androidx.compose.foundation.layout.PaddingValues(AppSpacing.screen),
        verticalArrangement = Arrangement.spacedBy(AppSpacing.content),
    ) {
        item {
            Text(
                text = detail.name,
                modifier = Modifier.semantics { heading() },
                style = MaterialTheme.typography.headlineMedium,
            )
        }
        item { Text(text = stringResource(detail.category.labelRes)) }
        item { Text(text = stringResource(R.string.poi_detail_city, detail.city)) }
        detail.area?.let { area ->
            item { Text(text = stringResource(R.string.poi_detail_area, area)) }
        }
        detail.address?.let { address ->
            item { Text(text = stringResource(R.string.poi_detail_address, address)) }
        }
        detail.shortDescription?.let { description ->
            item { Text(text = description) }
        }
        detail.navigationTarget?.let { target ->
            item {
                Button(onClick = { onNavigate(target) }) {
                    Text(text = stringResource(R.string.poi_detail_navigate))
                }
            }
            navigationError?.let { error ->
                item {
                    Text(
                        text = stringResource(error.messageRes),
                        color = MaterialTheme.colorScheme.error,
                    )
                }
            }
        }
        val displayableMenuItems = detail.menuItems.mapNotNull(::formatMenuItem)
        if (displayableMenuItems.isNotEmpty()) {
            item {
                Text(
                    text = stringResource(R.string.poi_detail_menu_title),
                    modifier = Modifier.semantics { heading() },
                    style = MaterialTheme.typography.titleMedium,
                )
            }
            items(displayableMenuItems) { item ->
                Column(verticalArrangement = Arrangement.spacedBy(AppSpacing.content / 2)) {
                    Text(text = item.dishName, style = MaterialTheme.typography.titleSmall)
                    Text(text = item.formattedPrice)
                    Text(text = stringResource(R.string.poi_detail_price_source, item.sourceType))
                    Text(text = stringResource(R.string.poi_detail_price_updated, item.updateDate))
                    HorizontalDivider()
                }
            }
        }
        detail.narration?.let { narration ->
            item {
                Text(
                    text = stringResource(R.string.poi_detail_narration_title),
                    modifier = Modifier.semantics { heading() },
                    style = MaterialTheme.typography.titleMedium,
                )
            }
            item { Text(text = narration.content) }
            item {
                Text(text = stringResource(R.string.poi_detail_narration_source, narration.sourceLabel))
            }
        }
    }
}

enum class PoiNavigationError(val messageRes: Int) {
    NO_COMPATIBLE_APPLICATION(R.string.poi_detail_navigation_unavailable),
    INVALID_DESTINATION(R.string.poi_detail_navigation_invalid_destination),
    LAUNCH_FAILED(R.string.poi_detail_navigation_launch_failed),
}

private fun ExternalNavigationResult.toPoiNavigationError(): PoiNavigationError? = when (this) {
    ExternalNavigationResult.Opened -> null
    ExternalNavigationResult.NoCompatibleApplication ->
        PoiNavigationError.NO_COMPATIBLE_APPLICATION
    ExternalNavigationResult.InvalidDestination -> PoiNavigationError.INVALID_DESTINATION
    ExternalNavigationResult.LaunchFailed -> PoiNavigationError.LAUNCH_FAILED
}

private fun formatMenuItem(item: PoiMenuItem): FormattedMenuItem? {
    if (item.dishName.isBlank() || item.sourceType.isBlank() || item.priceMinorUnits <= 0) return null
    val price = CurrencyFormatter.format(item.priceMinorUnits, item.currencyCode) ?: return null
    val updateDate = PriceUpdateDateFormatter.format(item.updatedAtEpochMillis) ?: return null
    return FormattedMenuItem(
        dishName = item.dishName,
        formattedPrice = price,
        sourceType = item.sourceType,
        updateDate = updateDate,
    )
}

private data class FormattedMenuItem(
    val dishName: String,
    val formattedPrice: String,
    val sourceType: String,
    val updateDate: String,
)
