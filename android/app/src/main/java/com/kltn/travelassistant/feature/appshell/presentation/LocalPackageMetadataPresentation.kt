package com.kltn.travelassistant.feature.appshell.presentation

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalConfiguration
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.res.stringResource
import com.kltn.travelassistant.R
import com.kltn.travelassistant.ui.theme.AppSpacing
import java.time.ZoneId

@Composable
fun LocalPackageMetadataSection(
    uiState: LocalPackageUiState,
    modifier: Modifier = Modifier,
) {
    Column(
        modifier = modifier
            .fillMaxWidth()
            .testTag(LOCAL_PACKAGE_METADATA_TEST_TAG),
        verticalArrangement = Arrangement.spacedBy(AppSpacing.content / 2),
    ) {
        Text(
            text = stringResource(R.string.local_package_title),
            style = MaterialTheme.typography.titleMedium,
        )
        when (uiState) {
            LocalPackageUiState.Loading -> PackageMetadataText(
                text = stringResource(R.string.local_package_loading),
            )
            LocalPackageUiState.Unavailable,
            LocalPackageUiState.Error -> PackageMetadataText(
                text = stringResource(R.string.local_package_unavailable),
            )
            is LocalPackageUiState.Available -> {
                PackageMetadataText(
                    text = stringResource(R.string.local_package_version, uiState.version),
                )
                PackagePublicationDateFormatter.format(
                    publishedAtEpochMillis = uiState.publishedAtEpochMillis,
                    locale = LocalConfiguration.current.locales[0],
                    zoneId = ZoneId.systemDefault(),
                )?.let { publicationDate ->
                    PackageMetadataText(
                        text = stringResource(
                            R.string.local_package_publication_date,
                            publicationDate,
                        ),
                    )
                }
            }
        }
    }
}

@Composable
private fun PackageMetadataText(text: String) {
    Text(
        text = text,
        color = MaterialTheme.colorScheme.onSurfaceVariant,
        style = MaterialTheme.typography.bodySmall,
    )
}

internal const val LOCAL_PACKAGE_METADATA_TEST_TAG = "local-package-metadata"
