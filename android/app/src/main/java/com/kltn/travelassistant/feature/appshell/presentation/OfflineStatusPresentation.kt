package com.kltn.travelassistant.feature.appshell.presentation

import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.Row
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Close
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.res.stringResource
import com.kltn.travelassistant.R
import com.kltn.travelassistant.ui.theme.AppSpacing

@Composable
fun AppShellStatusPresentation(
    connectivityUiState: ConnectivityUiState,
    shouldShowOfflineWarning: Boolean,
    onDismissOfflineWarning: () -> Unit,
    modifier: Modifier = Modifier,
) {
    when (connectivityUiState) {
        ConnectivityUiState.Checking -> Text(
            text = stringResource(R.string.connectivity_checking),
            modifier = modifier
                .fillMaxWidth()
                .padding(
                    horizontal = AppSpacing.content,
                    vertical = AppSpacing.content / 2,
                ),
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            style = MaterialTheme.typography.bodyMedium,
        )
        ConnectivityUiState.Online -> Unit
        ConnectivityUiState.Offline -> if (shouldShowOfflineWarning) {
            OfflineWarning(
                onDismiss = onDismissOfflineWarning,
                modifier = modifier,
            )
        }
    }
}

@Composable
private fun OfflineWarning(
    onDismiss: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Surface(
        modifier = modifier
            .fillMaxWidth()
            .testTag(OFFLINE_WARNING_TEST_TAG),
        color = MaterialTheme.colorScheme.errorContainer,
        contentColor = MaterialTheme.colorScheme.onErrorContainer,
    ) {
        Row(
            modifier = Modifier.padding(
                start = AppSpacing.content,
                end = AppSpacing.content / 2,
            ),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Text(
                text = stringResource(R.string.connectivity_offline),
                modifier = Modifier
                    .weight(1f)
                    .padding(vertical = AppSpacing.content),
                style = MaterialTheme.typography.bodyMedium,
            )
            IconButton(onClick = onDismiss) {
                Icon(
                    imageVector = Icons.Filled.Close,
                    contentDescription = stringResource(
                        R.string.connectivity_offline_dismiss,
                    ),
                )
            }
        }
    }
}

internal const val OFFLINE_WARNING_TEST_TAG = "offline-warning"
