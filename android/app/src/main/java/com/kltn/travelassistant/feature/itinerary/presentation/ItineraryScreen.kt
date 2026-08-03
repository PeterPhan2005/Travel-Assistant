package com.kltn.travelassistant.feature.itinerary.presentation

import androidx.annotation.StringRes
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.selection.selectable
import androidx.compose.foundation.selection.selectableGroup
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.RadioButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import com.kltn.travelassistant.R
import com.kltn.travelassistant.feature.itinerary.domain.ItineraryCity
import com.kltn.travelassistant.feature.itinerary.domain.ItineraryDraft
import com.kltn.travelassistant.feature.itinerary.domain.ItineraryDraftFailure
import com.kltn.travelassistant.feature.itinerary.domain.MAX_ITINERARY_NOTES_CODE_POINTS
import com.kltn.travelassistant.ui.theme.AppSpacing

internal const val ITINERARY_TIMELINE_TEST_TAG = "itinerary_timeline"
internal const val ITINERARY_GENERATE_TEST_TAG = "itinerary_generate"
internal const val ITINERARY_SAVE_TEST_TAG = "itinerary_save"
internal const val ITINERARY_HEADING_TEST_TAG = "itinerary_heading"
internal const val ITINERARY_BODY_TEST_TAG = "itinerary_body"

@Composable
internal fun ItineraryScreen(
    uiState: ItineraryUiState,
    onCitySelected: (ItineraryCity) -> Unit,
    onLocalDateChanged: (String) -> Unit,
    onStartTimeChanged: (String) -> Unit,
    onEndTimeChanged: (String) -> Unit,
    onMaximumStopsChanged: (String) -> Unit,
    onNotesChanged: (String) -> Unit,
    onGenerate: () -> Unit,
    onCancelGeneration: () -> Unit,
    onRetry: () -> Unit,
    onSave: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Column(
        modifier = modifier
            .fillMaxSize()
            .padding(AppSpacing.screen),
        verticalArrangement = Arrangement.spacedBy(AppSpacing.content),
    ) {
        Text(
            text = stringResource(R.string.destination_itinerary),
            style = MaterialTheme.typography.headlineMedium,
            modifier = Modifier
                .testTag(ITINERARY_HEADING_TEST_TAG)
                .semantics { heading() },
        )
        LazyColumn(
            modifier = Modifier
                .fillMaxWidth()
                .weight(1f)
                .testTag(ITINERARY_BODY_TEST_TAG),
            verticalArrangement = Arrangement.spacedBy(AppSpacing.content),
        ) {
            item {
                Text(
                    text = stringResource(R.string.itinerary_explanation),
                    style = MaterialTheme.typography.bodyLarge,
                )
            }
            item {
                CitySelector(
                    selectedCity = uiState.form.city,
                    error = uiState.fieldErrors.city,
                    onCitySelected = onCitySelected,
                )
            }
            item {
                ItineraryTextField(
                    value = uiState.form.localDate,
                    onValueChange = onLocalDateChanged,
                    labelRes = R.string.itinerary_date_label,
                    placeholderRes = R.string.itinerary_date_placeholder,
                    error = uiState.fieldErrors.localDate,
                    keyboardType = KeyboardType.Text,
                )
            }
            item {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(AppSpacing.content),
                ) {
                    ItineraryTextField(
                        value = uiState.form.startLocalTime,
                        onValueChange = onStartTimeChanged,
                        labelRes = R.string.itinerary_start_time_label,
                        placeholderRes = R.string.itinerary_time_placeholder,
                        error = uiState.fieldErrors.startLocalTime,
                        keyboardType = KeyboardType.Text,
                        modifier = Modifier.weight(1f),
                    )
                    ItineraryTextField(
                        value = uiState.form.endLocalTime,
                        onValueChange = onEndTimeChanged,
                        labelRes = R.string.itinerary_end_time_label,
                        placeholderRes = R.string.itinerary_time_placeholder,
                        error = uiState.fieldErrors.endLocalTime,
                        keyboardType = KeyboardType.Text,
                        modifier = Modifier.weight(1f),
                    )
                }
            }
            item {
                ItineraryTextField(
                    value = uiState.form.maximumStops,
                    onValueChange = onMaximumStopsChanged,
                    labelRes = R.string.itinerary_maximum_stops_label,
                    placeholderRes = R.string.itinerary_maximum_stops_placeholder,
                    error = uiState.fieldErrors.maximumStops,
                    keyboardType = KeyboardType.Number,
                )
            }
            item {
                OutlinedTextField(
                    value = uiState.form.notes,
                    onValueChange = onNotesChanged,
                    label = { Text(stringResource(R.string.itinerary_notes_label)) },
                    placeholder = {
                        Text(stringResource(R.string.itinerary_notes_placeholder))
                    },
                    minLines = 3,
                    maxLines = 5,
                    isError = uiState.fieldErrors.notes != null,
                    supportingText = {
                        val error = uiState.fieldErrors.notes
                        if (error != null) {
                            ValidationMessage(error)
                        } else {
                            Text(
                                stringResource(
                                    R.string.itinerary_notes_count,
                                    uiState.form.notes.codePointCount(
                                        0,
                                        uiState.form.notes.length,
                                    ),
                                    MAX_ITINERARY_NOTES_CODE_POINTS,
                                ),
                            )
                        }
                    },
                    modifier = Modifier.fillMaxWidth(),
                )
            }
            item {
                Button(
                    onClick = onGenerate,
                    enabled = uiState.generationState != ItineraryGenerationUiState.Loading,
                    modifier = Modifier
                        .fillMaxWidth()
                        .testTag(ITINERARY_GENERATE_TEST_TAG),
                ) {
                    Text(stringResource(R.string.itinerary_generate))
                }
            }
            item {
                GenerationPresentation(
                    state = uiState.generationState,
                    onCancel = onCancelGeneration,
                    onRetry = onRetry,
                )
            }
            item {
                SavePresentation(
                    generationState = uiState.generationState,
                    saveState = uiState.saveState,
                    onSave = onSave,
                )
            }
        }
    }
}

@Composable
private fun CitySelector(
    selectedCity: ItineraryCity?,
    error: ItineraryValidationError?,
    onCitySelected: (ItineraryCity) -> Unit,
) {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .selectableGroup()
            .semantics {
                contentDescription = "Chọn thành phố cho lịch trình"
            },
    ) {
        Text(
            text = stringResource(R.string.itinerary_city_label),
            style = MaterialTheme.typography.titleMedium,
        )
        ItineraryCity.entries.forEach { city ->
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .height(48.dp)
                    .selectable(
                        selected = selectedCity == city,
                        onClick = { onCitySelected(city) },
                        role = Role.RadioButton,
                    ),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                RadioButton(
                    selected = selectedCity == city,
                    onClick = null,
                )
                Spacer(Modifier.width(8.dp))
                Text(stringResource(city.labelRes()))
            }
        }
        error?.let { ValidationMessage(it) }
    }
}

@Composable
private fun ItineraryTextField(
    value: String,
    onValueChange: (String) -> Unit,
    @StringRes labelRes: Int,
    @StringRes placeholderRes: Int,
    error: ItineraryValidationError?,
    keyboardType: KeyboardType,
    modifier: Modifier = Modifier,
) {
    OutlinedTextField(
        value = value,
        onValueChange = onValueChange,
        label = { Text(stringResource(labelRes)) },
        placeholder = { Text(stringResource(placeholderRes)) },
        singleLine = true,
        isError = error != null,
        keyboardOptions = KeyboardOptions(keyboardType = keyboardType),
        supportingText = error?.let {
            {
                ValidationMessage(it)
            }
        },
        modifier = modifier.fillMaxWidth(),
    )
}

@Composable
private fun ValidationMessage(error: ItineraryValidationError) {
    Text(
        text = stringResource(error.messageRes()),
        color = MaterialTheme.colorScheme.error,
    )
}

@Composable
private fun GenerationPresentation(
    state: ItineraryGenerationUiState,
    onCancel: () -> Unit,
    onRetry: () -> Unit,
) {
    when (state) {
        ItineraryGenerationUiState.Idle -> Unit
        ItineraryGenerationUiState.Loading -> {
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .semantics {
                        liveRegion = LiveRegionMode.Polite
                        contentDescription = "Đang tạo lịch trình nháp"
                    },
                verticalAlignment = Alignment.CenterVertically,
            ) {
                CircularProgressIndicator()
                Spacer(Modifier.width(AppSpacing.content))
                Text(
                    text = stringResource(R.string.itinerary_loading),
                    modifier = Modifier.weight(1f),
                )
            }
            OutlinedButton(
                onClick = onCancel,
                modifier = Modifier.fillMaxWidth(),
            ) {
                Text(stringResource(R.string.itinerary_cancel_generation))
            }
        }
        is ItineraryGenerationUiState.Content -> Timeline(state.draft)
        ItineraryGenerationUiState.Cancelled -> StatusMessage(
            textRes = R.string.itinerary_cancelled,
        )
        is ItineraryGenerationUiState.Error -> {
            StatusMessage(textRes = state.reason.messageRes())
            if (state.reason.retryable) {
                OutlinedButton(
                    onClick = onRetry,
                    modifier = Modifier.fillMaxWidth(),
                ) {
                    Text(stringResource(R.string.itinerary_retry))
                }
            }
        }
        ItineraryGenerationUiState.Unavailable -> StatusMessage(
            textRes = R.string.itinerary_transport_unavailable,
        )
    }
}

@Composable
private fun Timeline(draft: ItineraryDraft) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .testTag(ITINERARY_TIMELINE_TEST_TAG)
            .semantics {
                contentDescription = "Dòng thời gian lịch trình nháp"
            },
    ) {
        Column(
            modifier = Modifier.padding(AppSpacing.content),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Text(
                text = stringResource(R.string.itinerary_draft_only),
                style = MaterialTheme.typography.labelLarge,
                color = MaterialTheme.colorScheme.primary,
            )
            Text(
                text = stringResource(
                    R.string.itinerary_timeline_context,
                    draft.localDate.toString(),
                    stringResource(draft.city.labelRes()),
                    draft.timezone,
                ),
                style = MaterialTheme.typography.titleMedium,
                modifier = Modifier.semantics { heading() },
            )
            draft.items.forEachIndexed { index, item ->
                if (index > 0) HorizontalDivider()
                Column(
                    modifier = Modifier.semantics {
                        contentDescription =
                            "Điểm dừng ${index + 1}: ${item.title}, " +
                            "${item.startLocalTime} đến ${item.endLocalTime}"
                    },
                ) {
                    Text(
                        text = "${item.startLocalTime}–${item.endLocalTime}",
                        style = MaterialTheme.typography.labelLarge,
                    )
                    Text(
                        text = item.title,
                        style = MaterialTheme.typography.titleMedium,
                    )
                }
            }
            Text(
                text = stringResource(R.string.itinerary_assumptions_title),
                style = MaterialTheme.typography.titleMedium,
                modifier = Modifier.semantics { heading() },
            )
            draft.assumptions.forEach { assumption ->
                Text("• $assumption")
            }
            if (draft.warnings.isNotEmpty()) {
                Column(
                    modifier = Modifier.semantics {
                        liveRegion = LiveRegionMode.Polite
                        contentDescription = "Các lưu ý của lịch trình nháp"
                    },
                ) {
                    Text(
                        text = stringResource(R.string.itinerary_warnings_title),
                        style = MaterialTheme.typography.titleMedium,
                        color = MaterialTheme.colorScheme.tertiary,
                        modifier = Modifier.semantics { heading() },
                    )
                    draft.warnings.forEach { warning ->
                        Text("• ${warning.message}")
                    }
                }
            }
        }
    }
}

@Composable
private fun SavePresentation(
    generationState: ItineraryGenerationUiState,
    saveState: ItinerarySaveUiState,
    onSave: () -> Unit,
) {
    val hasDraft = generationState is ItineraryGenerationUiState.Content
    Button(
        onClick = onSave,
        enabled = hasDraft && saveState != ItinerarySaveUiState.Saving,
        modifier = Modifier
            .fillMaxWidth()
            .testTag(ITINERARY_SAVE_TEST_TAG),
    ) {
        Text(stringResource(R.string.itinerary_save))
    }
    when (saveState) {
        ItinerarySaveUiState.Idle -> Unit
        ItinerarySaveUiState.Saving -> StatusMessage(R.string.itinerary_saving)
        ItinerarySaveUiState.Saved -> StatusMessage(R.string.itinerary_saved)
        ItinerarySaveUiState.PersistenceUnavailable -> StatusMessage(
            R.string.itinerary_persistence_unavailable,
        )
        ItinerarySaveUiState.Failed -> StatusMessage(R.string.itinerary_save_failed)
    }
}

@Composable
private fun StatusMessage(@StringRes textRes: Int) {
    Text(
        text = stringResource(textRes),
        modifier = Modifier.semantics {
            liveRegion = LiveRegionMode.Polite
        },
    )
}

@StringRes
private fun ItineraryCity.labelRes(): Int = when (this) {
    ItineraryCity.HO_CHI_MINH_CITY -> R.string.itinerary_city_hcmc
    ItineraryCity.BANGKOK -> R.string.itinerary_city_bangkok
}

@StringRes
private fun ItineraryValidationError.messageRes(): Int = when (this) {
    ItineraryValidationError.CITY_REQUIRED -> R.string.itinerary_error_city_required
    ItineraryValidationError.DATE_REQUIRED -> R.string.itinerary_error_date_required
    ItineraryValidationError.DATE_INVALID -> R.string.itinerary_error_date_invalid
    ItineraryValidationError.START_TIME_REQUIRED ->
        R.string.itinerary_error_start_time_required
    ItineraryValidationError.START_TIME_INVALID ->
        R.string.itinerary_error_start_time_invalid
    ItineraryValidationError.END_TIME_REQUIRED -> R.string.itinerary_error_end_time_required
    ItineraryValidationError.END_TIME_INVALID -> R.string.itinerary_error_end_time_invalid
    ItineraryValidationError.END_NOT_AFTER_START ->
        R.string.itinerary_error_end_not_after_start
    ItineraryValidationError.MAXIMUM_STOPS_REQUIRED ->
        R.string.itinerary_error_maximum_stops_required
    ItineraryValidationError.MAXIMUM_STOPS_NOT_INTEGER ->
        R.string.itinerary_error_maximum_stops_not_integer
    ItineraryValidationError.MAXIMUM_STOPS_OUT_OF_RANGE ->
        R.string.itinerary_error_maximum_stops_out_of_range
    ItineraryValidationError.NOTES_TOO_LONG -> R.string.itinerary_error_notes_too_long
}

@StringRes
private fun ItineraryDraftFailure.messageRes(): Int = when (this) {
    ItineraryDraftFailure.OFFLINE -> R.string.itinerary_error_offline
    ItineraryDraftFailure.AUTHENTICATION_REQUIRED ->
        R.string.itinerary_error_authentication_required
    ItineraryDraftFailure.INVALID_REQUEST -> R.string.itinerary_error_invalid_request
    ItineraryDraftFailure.TIMEOUT -> R.string.itinerary_error_timeout
    ItineraryDraftFailure.RATE_LIMITED -> R.string.itinerary_error_rate_limited
    ItineraryDraftFailure.UNAVAILABLE -> R.string.itinerary_error_unavailable
    ItineraryDraftFailure.INVALID_RESPONSE -> R.string.itinerary_error_invalid_response
    ItineraryDraftFailure.UNSUPPORTED_TRANSPORT ->
        R.string.itinerary_transport_unavailable
}
