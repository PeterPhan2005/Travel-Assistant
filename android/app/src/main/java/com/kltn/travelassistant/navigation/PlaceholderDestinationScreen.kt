package com.kltn.travelassistant.navigation

import androidx.annotation.StringRes
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.semantics
import com.kltn.travelassistant.R
import com.kltn.travelassistant.ui.theme.AppSpacing

@Composable
fun PlaceholderDestinationScreen(
    @StringRes titleRes: Int,
    modifier: Modifier = Modifier,
    @StringRes unavailableExplanationRes: Int? = null,
    additionalContent: @Composable ColumnScope.() -> Unit = {},
) {
    Column(
        modifier = modifier
            .fillMaxSize()
            .padding(AppSpacing.screen),
        verticalArrangement = Arrangement.spacedBy(AppSpacing.content),
    ) {
        Text(
            text = stringResource(titleRes),
            modifier = Modifier.semantics { heading() },
            style = MaterialTheme.typography.headlineMedium,
        )
        Text(
            text = stringResource(R.string.feature_coming_later),
            style = MaterialTheme.typography.bodyLarge,
        )
        unavailableExplanationRes?.let { explanationRes ->
            Text(
                text = stringResource(explanationRes),
                color = MaterialTheme.colorScheme.error,
                style = MaterialTheme.typography.bodyMedium,
            )
        }
        additionalContent()
    }
}
