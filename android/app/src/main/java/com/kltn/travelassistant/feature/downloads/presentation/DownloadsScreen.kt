package com.kltn.travelassistant.feature.downloads.presentation

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalConfiguration
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.semantics
import com.kltn.travelassistant.R
import com.kltn.travelassistant.feature.appshell.presentation.ConnectivityUiState
import com.kltn.travelassistant.feature.appshell.presentation.LOCAL_PACKAGE_METADATA_TEST_TAG
import com.kltn.travelassistant.feature.appshell.presentation.PackagePublicationDateFormatter
import com.kltn.travelassistant.feature.downloads.domain.PackageOrigin
import com.kltn.travelassistant.feature.downloads.domain.PackageSyncFailureCode
import com.kltn.travelassistant.feature.downloads.domain.PackageSyncPhase
import com.kltn.travelassistant.ui.theme.AppSpacing
import java.time.ZoneId

@Composable
fun DownloadsScreen(
    uiState: DownloadsUiState,
    connectivity: ConnectivityUiState,
    onDownload: () -> Unit,
    onRetry: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Column(
        modifier = modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(AppSpacing.screen),
        verticalArrangement = Arrangement.spacedBy(AppSpacing.content),
    ) {
        Text(
            text = stringResource(R.string.destination_downloads),
            modifier = Modifier.semantics { heading() },
            style = MaterialTheme.typography.headlineMedium,
        )
        Card(
            modifier = Modifier
                .fillMaxWidth()
                .testTag(LOCAL_PACKAGE_METADATA_TEST_TAG),
        ) {
            Column(
                modifier = Modifier.padding(AppSpacing.content),
                verticalArrangement = Arrangement.spacedBy(AppSpacing.content / 2),
            ) {
                Text(
                    text = stringResource(R.string.downloads_hcmc_title),
                    style = MaterialTheme.typography.titleLarge,
                )
                Text(
                    text = stringResource(R.string.local_package_title),
                    style = MaterialTheme.typography.titleMedium,
                )
                ActivePackageContent(uiState)
                SyncStatusContent(uiState)
                if (connectivity == ConnectivityUiState.Offline) {
                    Text(
                        text = stringResource(R.string.downloads_offline_explanation),
                        color = MaterialTheme.colorScheme.error,
                        style = MaterialTheme.typography.bodyMedium,
                    )
                }
                ActionButton(
                    uiState = uiState,
                    enabled = connectivity == ConnectivityUiState.Online,
                    onDownload = onDownload,
                    onRetry = onRetry,
                )
            }
        }
    }
}

@Composable
private fun ActivePackageContent(uiState: DownloadsUiState) {
    when {
        uiState.isLoading -> Text(stringResource(R.string.local_package_loading))
        uiState.activePackage == null -> Text(
            stringResource(R.string.local_package_unavailable),
        )
        else -> {
            val active = uiState.activePackage
            Text(
                text = stringResource(
                    if (active.origin == PackageOrigin.BUNDLED) {
                        R.string.downloads_bundled_active
                    } else {
                        R.string.downloads_downloaded_active
                    },
                ),
            )
            Text(
                text = stringResource(
                    R.string.local_package_version,
                    active.contentVersion,
                ),
            )
            PackagePublicationDateFormatter.format(
                publishedAtEpochMillis = active.publishedAtEpochMillis,
                locale = LocalConfiguration.current.locales[0],
                zoneId = ZoneId.systemDefault(),
            )?.let { date ->
                Text(
                    text = stringResource(R.string.local_package_publication_date, date),
                )
            }
        }
    }
}

@Composable
private fun SyncStatusContent(uiState: DownloadsUiState) {
    when (val status = uiState.status) {
        DownloadsStatus.Idle -> Unit
        DownloadsStatus.Success -> Text(
            text = stringResource(R.string.downloads_sync_success),
            color = MaterialTheme.colorScheme.primary,
        )
        is DownloadsStatus.InProgress -> {
            CircularProgressIndicator()
            Text(text = stringResource(status.phase.labelResource()))
        }
        is DownloadsStatus.Failure -> {
            Text(
                text = stringResource(status.code.errorResource()),
                color = MaterialTheme.colorScheme.error,
            )
            if (uiState.activePackage != null) {
                Text(text = stringResource(R.string.downloads_previous_data_preserved))
            }
        }
    }
}

@Composable
private fun ActionButton(
    uiState: DownloadsUiState,
    enabled: Boolean,
    onDownload: () -> Unit,
    onRetry: () -> Unit,
) {
    val status = uiState.status
    Button(
        onClick = if (status is DownloadsStatus.Failure) onRetry else onDownload,
        enabled = enabled &&
            !uiState.isLoading &&
            status !is DownloadsStatus.InProgress,
    ) {
        Text(
            text = stringResource(
                when {
                    status is DownloadsStatus.Failure -> R.string.downloads_retry
                    uiState.activePackage == null -> R.string.downloads_download
                    else -> R.string.downloads_update
                },
            ),
        )
    }
}

private fun PackageSyncPhase.labelResource(): Int = when (this) {
    PackageSyncPhase.QUEUED -> R.string.downloads_phase_queued
    PackageSyncPhase.DOWNLOADING_MANIFEST -> R.string.downloads_phase_manifest
    PackageSyncPhase.DOWNLOADING_DATA -> R.string.downloads_phase_data
    PackageSyncPhase.VERIFYING -> R.string.downloads_phase_verifying
    PackageSyncPhase.VALIDATING -> R.string.downloads_phase_validating
    PackageSyncPhase.ACTIVATING -> R.string.downloads_phase_activating
}

private fun PackageSyncFailureCode.errorResource(): Int = when (this) {
    PackageSyncFailureCode.NETWORK_UNAVAILABLE -> R.string.downloads_error_network
    PackageSyncFailureCode.TEMPORARY_SERVER_FAILURE -> R.string.downloads_error_server
    PackageSyncFailureCode.INVALID_MANIFEST,
    PackageSyncFailureCode.UNSUPPORTED_PACKAGE,
    PackageSyncFailureCode.CHECKSUM_MISMATCH,
    PackageSyncFailureCode.INVALID_DATA -> R.string.downloads_error_invalid_package
    PackageSyncFailureCode.ACTIVATION_FAILED -> R.string.downloads_error_activation
    PackageSyncFailureCode.CANCELLED -> R.string.downloads_error_cancelled
}
