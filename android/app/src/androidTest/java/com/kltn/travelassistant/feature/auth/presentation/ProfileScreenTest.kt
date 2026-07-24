package com.kltn.travelassistant.feature.auth.presentation

import androidx.compose.ui.test.assertCountEquals
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.assertIsEnabled
import androidx.compose.ui.test.assertIsNotEnabled
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onAllNodesWithText
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performScrollTo
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.kltn.travelassistant.R
import com.kltn.travelassistant.feature.auth.domain.AuthSession
import com.kltn.travelassistant.feature.auth.domain.AuthUser
import com.kltn.travelassistant.feature.auth.domain.EmailValidationError
import com.kltn.travelassistant.feature.auth.domain.PasswordConfirmationValidationError
import com.kltn.travelassistant.feature.auth.domain.PasswordValidationError
import com.kltn.travelassistant.ui.theme.TravelAssistantTheme
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class ProfileScreenTest {
    @get:Rule
    val composeRule = createComposeRule()

    @Test
    fun signedOutSignInFormIsAccessibleAndCanSwitchModes() {
        var requestedMode: AuthFormMode? = null
        setProfileContent(
            state = ProfileUiState(session = AuthSession.SignedOut),
            onFormModeChanged = { requestedMode = it },
        )

        composeRule.onAllNodesWithText(getString(R.string.auth_sign_in)).assertCountEquals(2)
        composeRule.onNodeWithText(getString(R.string.auth_sign_up)).assertIsDisplayed()
        composeRule.onNodeWithTag(PROFILE_EMAIL_TEST_TAG).assertIsDisplayed().assertIsEnabled()
        composeRule.onNodeWithTag(PROFILE_PASSWORD_TEST_TAG).assertIsDisplayed().assertIsEnabled()
        composeRule.onNodeWithText(getString(R.string.auth_sign_up)).performClick()

        assertEquals(AuthFormMode.SIGN_UP, requestedMode)
    }

    @Test
    fun signUpFormShowsConfirmationField() {
        setProfileContent(
            ProfileUiState(
                session = AuthSession.SignedOut,
                formMode = AuthFormMode.SIGN_UP,
            ),
        )

        composeRule.onNodeWithTag(PROFILE_PASSWORD_CONFIRMATION_TEST_TAG)
            .performScrollTo()
            .assertIsDisplayed()
    }

    @Test
    fun localizedValidationErrorsRenderNearFields() {
        setProfileContent(
            ProfileUiState(
                session = AuthSession.SignedOut,
                formMode = AuthFormMode.SIGN_UP,
                emailError = EmailValidationError.MALFORMED,
                passwordError = PasswordValidationError.TOO_SHORT,
                passwordConfirmationError = PasswordConfirmationValidationError.DOES_NOT_MATCH,
            ),
        )

        composeRule.onNodeWithText(getString(R.string.auth_email_invalid)).assertIsDisplayed()
        composeRule.onNodeWithText(getString(R.string.auth_password_too_short)).assertIsDisplayed()
        composeRule.onNodeWithText(getString(R.string.auth_password_confirmation_mismatch))
            .performScrollTo()
            .assertIsDisplayed()
    }

    @Test
    fun loadingDisablesSubmissionWithoutBlockingOtherDestinations() {
        setProfileContent(
            ProfileUiState(
                session = AuthSession.SignedOut,
                activeOperation = AuthOperation.SIGN_IN,
            ),
        )

        composeRule.onNodeWithTag(PROFILE_SUBMIT_TEST_TAG)
            .performScrollTo()
            .assertIsNotEnabled()
        composeRule.onNodeWithText(getString(R.string.auth_loading))
            .performScrollTo()
            .assertIsDisplayed()
    }

    @Test
    fun verificationRequiredShowsEmailAndAllExplicitActions() {
        var refreshRequested = false
        var resendRequested = false
        var signOutRequested = false
        setProfileContent(
            state = ProfileUiState(
                session = AuthSession.VerificationRequired(unverifiedUser),
            ),
            onRefreshVerification = { refreshRequested = true },
            onResendVerificationEmail = { resendRequested = true },
            onSignOut = { signOutRequested = true },
        )

        composeRule.onNodeWithText(getString(R.string.auth_account_email, email))
            .assertIsDisplayed()
        composeRule.onNodeWithText(getString(R.string.auth_verification_refresh))
            .performClick()
        composeRule.onNodeWithText(getString(R.string.auth_verification_resend))
            .performScrollTo()
            .performClick()
        composeRule.onNodeWithText(getString(R.string.auth_sign_out))
            .performScrollTo()
            .performClick()

        assertTrue(refreshRequested)
        assertTrue(resendRequested)
        assertTrue(signOutRequested)
    }

    @Test
    fun authenticatedShowsVerifiedEmailAndSignOutWithoutUidOrTokens() {
        var signOutRequested = false
        setProfileContent(
            state = ProfileUiState(
                session = AuthSession.Authenticated(verifiedUser),
            ),
            onSignOut = { signOutRequested = true },
        )

        composeRule.onNodeWithText(getString(R.string.auth_authenticated_title))
            .assertIsDisplayed()
        composeRule.onNodeWithText(getString(R.string.auth_account_email, email))
            .assertIsDisplayed()
        composeRule.onAllNodesWithText("uid-private", substring = true).assertCountEquals(0)
        composeRule.onAllNodesWithText("token", substring = true, ignoreCase = true)
            .assertCountEquals(0)
        composeRule.onNodeWithText(getString(R.string.auth_sign_out)).performClick()

        assertTrue(signOutRequested)
    }

    @Test
    fun controlledFailureNeverDisplaysRawFirebaseExceptionText() {
        setProfileContent(
            ProfileUiState(
                session = AuthSession.SignedOut,
                message = ProfileMessage.GENERIC_FAILURE,
            ),
        )

        composeRule.onNodeWithText(getString(R.string.auth_generic_failure))
            .performScrollTo()
            .assertIsDisplayed()
        composeRule.onAllNodesWithText("FirebaseAuthException", substring = true)
            .assertCountEquals(0)
    }

    private fun setProfileContent(
        state: ProfileUiState,
        onFormModeChanged: (AuthFormMode) -> Unit = {},
        onRefreshVerification: () -> Unit = {},
        onResendVerificationEmail: () -> Unit = {},
        onSignOut: () -> Unit = {},
    ) {
        composeRule.setContent {
            TravelAssistantTheme {
                ProfileScreen(
                    uiState = state,
                    onFormModeChanged = onFormModeChanged,
                    onEmailChanged = {},
                    onPasswordChanged = {},
                    onPasswordConfirmationChanged = {},
                    onSubmit = {},
                    onRefreshVerification = onRefreshVerification,
                    onResendVerificationEmail = onResendVerificationEmail,
                    onSignOut = onSignOut,
                    onRetrySession = {},
                )
            }
        }
    }

    private fun getString(resourceId: Int, vararg formatArgs: Any): String =
        ApplicationProvider.getApplicationContext<android.content.Context>()
            .getString(resourceId, *formatArgs)

    private companion object {
        const val email = "traveler@example.com"
        val unverifiedUser = AuthUser("uid-private", email, false)
        val verifiedUser = unverifiedUser.copy(isEmailVerified = true)
    }
}
