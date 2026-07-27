package com.kltn.travelassistant.feature.downloads.presentation

import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.assertIsEnabled
import androidx.compose.ui.test.assertIsNotEnabled
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.kltn.travelassistant.R
import com.kltn.travelassistant.feature.appshell.presentation.ConnectivityUiState
import com.kltn.travelassistant.feature.downloads.domain.ActivePackageMetadata
import com.kltn.travelassistant.feature.downloads.domain.PackageCity
import com.kltn.travelassistant.feature.downloads.domain.PackageOrigin
import com.kltn.travelassistant.feature.downloads.domain.PackageSyncFailureCode
import com.kltn.travelassistant.feature.downloads.domain.PackageSyncPhase
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class DownloadsScreenTest {
    @get:Rule
    val composeRule = createComposeRule()

    @Test
    fun bundledActiveAndVerifyingPhaseRenderWithoutFakePercentage() {
        setContent(
            DownloadsUiState(
                isLoading = false,
                activePackage = activePackage.copy(origin = PackageOrigin.BUNDLED),
                status = DownloadsStatus.InProgress(PackageSyncPhase.VERIFYING),
            ),
        )

        composeRule.onNodeWithText(string(R.string.downloads_bundled_active))
            .assertIsDisplayed()
        composeRule.onNodeWithText(string(R.string.downloads_phase_verifying))
            .assertIsDisplayed()
        composeRule.onNodeWithText(string(R.string.downloads_update))
            .assertIsNotEnabled()
    }

    @Test
    fun retryableFailureShowsPreservationAndInvokesRetry() {
        var retried = false
        setContent(
            DownloadsUiState(
                isLoading = false,
                activePackage = activePackage,
                status = DownloadsStatus.Failure(
                    PackageSyncFailureCode.NETWORK_UNAVAILABLE,
                ),
            ),
            onRetry = { retried = true },
        )

        composeRule.onNodeWithText(string(R.string.downloads_error_network))
            .assertIsDisplayed()
        composeRule.onNodeWithText(string(R.string.downloads_previous_data_preserved))
            .assertIsDisplayed()
        composeRule.onNodeWithText(string(R.string.downloads_retry))
            .assertIsEnabled()
            .performClick()
        assertTrue(retried)
    }

    @Test
    fun invalidPackageFailureDoesNotClaimSuccessAndOfflineDisablesRetry() {
        setContent(
            DownloadsUiState(
                isLoading = false,
                activePackage = activePackage,
                status = DownloadsStatus.Failure(
                    PackageSyncFailureCode.CHECKSUM_MISMATCH,
                ),
            ),
            connectivity = ConnectivityUiState.Offline,
        )

        composeRule.onNodeWithText(string(R.string.downloads_error_invalid_package))
            .assertIsDisplayed()
        composeRule.onNodeWithText(string(R.string.downloads_previous_data_preserved))
            .assertIsDisplayed()
        composeRule.onNodeWithText(string(R.string.downloads_retry))
            .assertIsNotEnabled()
    }

    private fun setContent(
        state: DownloadsUiState,
        connectivity: ConnectivityUiState = ConnectivityUiState.Online,
        onRetry: () -> Unit = {},
    ) {
        composeRule.setContent {
            DownloadsScreen(
                uiState = state,
                connectivity = connectivity,
                onDownload = {},
                onRetry = onRetry,
            )
        }
    }

    private fun string(id: Int): String =
        ApplicationProvider.getApplicationContext<android.content.Context>().getString(id)

    private companion object {
        val activePackage = ActivePackageMetadata(
            packageId = "hcmc-starter-v1",
            city = PackageCity.HCMC,
            contentVersion = "1.0.0",
            publishedAtEpochMillis = 1_785_085_200_000,
            origin = PackageOrigin.DOWNLOADED,
        )
    }
}
