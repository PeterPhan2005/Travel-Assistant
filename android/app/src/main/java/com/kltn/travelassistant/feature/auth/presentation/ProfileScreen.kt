package com.kltn.travelassistant.feature.auth.presentation

import androidx.compose.foundation.Image
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.password
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import com.kltn.travelassistant.R
import com.kltn.travelassistant.feature.auth.domain.AuthSession
import com.kltn.travelassistant.feature.auth.domain.EmailValidationError
import com.kltn.travelassistant.feature.auth.domain.PasswordConfirmationValidationError
import com.kltn.travelassistant.feature.auth.domain.PasswordValidationError
import com.kltn.travelassistant.ui.theme.AppSpacing

const val PROFILE_EMAIL_TEST_TAG = "profile-email"
const val PROFILE_PASSWORD_TEST_TAG = "profile-password"
const val PROFILE_PASSWORD_CONFIRMATION_TEST_TAG = "profile-password-confirmation"
const val PROFILE_SUBMIT_TEST_TAG = "profile-submit"
const val PROFILE_GOOGLE_SIGN_IN_TEST_TAG = "profile-google-sign-in"
const val PROFILE_GOOGLE_SIGN_IN_LOGO_TEST_TAG = "google-sign-in-logo"

@Composable
fun ProfileScreen(
    uiState: ProfileUiState,
    onFormModeChanged: (AuthFormMode) -> Unit,
    onEmailChanged: (String) -> Unit,
    onPasswordChanged: (String) -> Unit,
    onPasswordConfirmationChanged: (String) -> Unit,
    onSubmit: () -> Unit,
    onGoogleSignIn: () -> Unit = {},
    onRefreshVerification: () -> Unit,
    onResendVerificationEmail: () -> Unit,
    onSignOut: () -> Unit,
    onRetrySession: () -> Unit,
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
            text = stringResource(R.string.destination_profile),
            style = MaterialTheme.typography.headlineMedium,
            modifier = Modifier.semantics { heading() },
        )
        when (val session = uiState.session) {
            AuthSession.Checking -> CheckingContent()
            AuthSession.SignedOut -> SignedOutContent(
                uiState = uiState,
                onFormModeChanged = onFormModeChanged,
                onEmailChanged = onEmailChanged,
                onPasswordChanged = onPasswordChanged,
                onPasswordConfirmationChanged = onPasswordConfirmationChanged,
                onSubmit = onSubmit,
                onGoogleSignIn = onGoogleSignIn,
            )
            is AuthSession.VerificationRequired -> VerificationRequiredContent(
                email = session.user.email,
                uiState = uiState,
                onRefreshVerification = onRefreshVerification,
                onResendVerificationEmail = onResendVerificationEmail,
                onSignOut = onSignOut,
            )
            is AuthSession.Authenticated -> AuthenticatedContent(
                email = session.user.email,
                isLoading = uiState.isLoading,
                onSignOut = onSignOut,
            )
            AuthSession.Error -> SessionErrorContent(onRetrySession)
        }
        uiState.message?.let { message ->
            Text(
                text = stringResource(message.stringResource()),
                color = if (message.isSuccess()) {
                    MaterialTheme.colorScheme.primary
                } else {
                    MaterialTheme.colorScheme.error
                },
            )
        }
    }
}

@Composable
private fun CheckingContent() {
    Row(
        horizontalArrangement = Arrangement.spacedBy(AppSpacing.content),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        CircularProgressIndicator()
        Text(stringResource(R.string.auth_session_checking))
    }
}

@Composable
private fun SignedOutContent(
    uiState: ProfileUiState,
    onFormModeChanged: (AuthFormMode) -> Unit,
    onEmailChanged: (String) -> Unit,
    onPasswordChanged: (String) -> Unit,
    onPasswordConfirmationChanged: (String) -> Unit,
    onSubmit: () -> Unit,
    onGoogleSignIn: () -> Unit,
) {
    Text(stringResource(R.string.auth_signed_out_explanation))
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.spacedBy(AppSpacing.content),
    ) {
        if (uiState.formMode == AuthFormMode.SIGN_IN) {
            Button(
                onClick = { onFormModeChanged(AuthFormMode.SIGN_IN) },
                enabled = !uiState.isLoading,
                modifier = Modifier.weight(1f),
            ) {
                Text(stringResource(R.string.auth_sign_in))
            }
            OutlinedButton(
                onClick = { onFormModeChanged(AuthFormMode.SIGN_UP) },
                enabled = !uiState.isLoading,
                modifier = Modifier.weight(1f),
            ) {
                Text(stringResource(R.string.auth_sign_up))
            }
        } else {
            OutlinedButton(
                onClick = { onFormModeChanged(AuthFormMode.SIGN_IN) },
                enabled = !uiState.isLoading,
                modifier = Modifier.weight(1f),
            ) {
                Text(stringResource(R.string.auth_sign_in))
            }
            Button(
                onClick = { onFormModeChanged(AuthFormMode.SIGN_UP) },
                enabled = !uiState.isLoading,
                modifier = Modifier.weight(1f),
            ) {
                Text(stringResource(R.string.auth_sign_up))
            }
        }
    }
    Text(
        text = stringResource(R.string.auth_or_separator),
        textAlign = TextAlign.Center,
        modifier = Modifier.fillMaxWidth(),
    )
    OutlinedButton(
        onClick = onGoogleSignIn,
        enabled = !uiState.isLoading,
        modifier = Modifier
            .fillMaxWidth()
            .testTag(PROFILE_GOOGLE_SIGN_IN_TEST_TAG),
    ) {
        Image(
            painter = painterResource(R.drawable.ic_google_g),
            contentDescription = null,
            modifier = Modifier
                .height(20.dp)
                .aspectRatio(200f / 204f)
                .testTag(PROFILE_GOOGLE_SIGN_IN_LOGO_TEST_TAG),
        )
        Spacer(Modifier.width(10.dp))
        Text(stringResource(R.string.auth_continue_with_google))
    }
    OutlinedTextField(
        value = uiState.email,
        onValueChange = onEmailChanged,
        label = { Text(stringResource(R.string.auth_email_label)) },
        singleLine = true,
        enabled = !uiState.isLoading,
        isError = uiState.emailError != null,
        supportingText = uiState.emailError?.let { error ->
            { Text(stringResource(error.stringResource())) }
        },
        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Email),
        modifier = Modifier
            .fillMaxWidth()
            .testTag(PROFILE_EMAIL_TEST_TAG),
    )
    PasswordField(
        value = uiState.password,
        onValueChange = onPasswordChanged,
        labelResource = R.string.auth_password_label,
        errorResource = uiState.passwordError?.stringResource(),
        enabled = !uiState.isLoading,
        testTag = PROFILE_PASSWORD_TEST_TAG,
    )
    if (uiState.formMode == AuthFormMode.SIGN_UP) {
        PasswordField(
            value = uiState.passwordConfirmation,
            onValueChange = onPasswordConfirmationChanged,
            labelResource = R.string.auth_password_confirmation_label,
            errorResource = uiState.passwordConfirmationError?.stringResource(),
            enabled = !uiState.isLoading,
            testTag = PROFILE_PASSWORD_CONFIRMATION_TEST_TAG,
        )
    }
    Button(
        onClick = onSubmit,
        enabled = !uiState.isLoading,
        modifier = Modifier
            .fillMaxWidth()
            .testTag(PROFILE_SUBMIT_TEST_TAG),
    ) {
        Text(
            stringResource(
                if (uiState.formMode == AuthFormMode.SIGN_IN) {
                    R.string.auth_sign_in
                } else {
                    R.string.auth_create_account
                },
            ),
        )
    }
    if (uiState.isLoading) {
        LoadingContent()
    }
}

@Composable
private fun PasswordField(
    value: String,
    onValueChange: (String) -> Unit,
    labelResource: Int,
    errorResource: Int?,
    enabled: Boolean,
    testTag: String,
) {
    OutlinedTextField(
        value = value,
        onValueChange = onValueChange,
        label = { Text(stringResource(labelResource)) },
        singleLine = true,
        enabled = enabled,
        isError = errorResource != null,
        supportingText = errorResource?.let { resource ->
            { Text(stringResource(resource)) }
        },
        visualTransformation = PasswordVisualTransformation(),
        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Password),
        modifier = Modifier
            .fillMaxWidth()
            .testTag(testTag)
            .semantics { password() },
    )
}

@Composable
private fun VerificationRequiredContent(
    email: String,
    uiState: ProfileUiState,
    onRefreshVerification: () -> Unit,
    onResendVerificationEmail: () -> Unit,
    onSignOut: () -> Unit,
) {
    Text(
        text = stringResource(R.string.auth_verification_required_title),
        style = MaterialTheme.typography.titleLarge,
    )
    Text(stringResource(R.string.auth_account_email, email))
    Text(stringResource(R.string.auth_verification_required_explanation))
    Button(
        onClick = onRefreshVerification,
        enabled = !uiState.isLoading,
        modifier = Modifier.fillMaxWidth(),
    ) {
        Text(stringResource(R.string.auth_verification_refresh))
    }
    OutlinedButton(
        onClick = onResendVerificationEmail,
        enabled = !uiState.isLoading,
        modifier = Modifier.fillMaxWidth(),
    ) {
        Text(stringResource(R.string.auth_verification_resend))
    }
    TextButton(
        onClick = onSignOut,
        enabled = !uiState.isLoading,
        modifier = Modifier.fillMaxWidth(),
    ) {
        Text(stringResource(R.string.auth_sign_out))
    }
    if (uiState.isLoading) {
        LoadingContent()
    }
}

@Composable
private fun AuthenticatedContent(
    email: String,
    isLoading: Boolean,
    onSignOut: () -> Unit,
) {
    Text(
        text = stringResource(R.string.auth_authenticated_title),
        style = MaterialTheme.typography.titleLarge,
    )
    Text(stringResource(R.string.auth_account_email, email))
    Text(stringResource(R.string.auth_authenticated_explanation))
    Button(
        onClick = onSignOut,
        enabled = !isLoading,
        modifier = Modifier.fillMaxWidth(),
    ) {
        Text(stringResource(R.string.auth_sign_out))
    }
    if (isLoading) {
        LoadingContent()
    }
}

@Composable
private fun SessionErrorContent(onRetrySession: () -> Unit) {
    Text(
        text = stringResource(R.string.auth_session_error),
        color = MaterialTheme.colorScheme.error,
    )
    Button(onClick = onRetrySession) {
        Text(stringResource(R.string.auth_retry))
    }
}

@Composable
private fun LoadingContent() {
    Row(
        horizontalArrangement = Arrangement.spacedBy(AppSpacing.content),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        CircularProgressIndicator()
        Text(stringResource(R.string.auth_loading))
    }
}

private fun EmailValidationError.stringResource(): Int = when (this) {
    EmailValidationError.REQUIRED -> R.string.auth_email_required
    EmailValidationError.MALFORMED -> R.string.auth_email_invalid
}

private fun PasswordValidationError.stringResource(): Int = when (this) {
    PasswordValidationError.REQUIRED -> R.string.auth_password_required
    PasswordValidationError.TOO_SHORT -> R.string.auth_password_too_short
}

private fun PasswordConfirmationValidationError.stringResource(): Int = when (this) {
    PasswordConfirmationValidationError.REQUIRED -> R.string.auth_password_confirmation_required
    PasswordConfirmationValidationError.DOES_NOT_MATCH ->
        R.string.auth_password_confirmation_mismatch
}

private fun ProfileMessage.stringResource(): Int = when (this) {
    ProfileMessage.VERIFICATION_EMAIL_SENT -> R.string.auth_verification_sent
    ProfileMessage.VERIFICATION_EMAIL_NOT_SENT -> R.string.auth_verification_send_failed
    ProfileMessage.VERIFICATION_STILL_REQUIRED -> R.string.auth_verification_still_required
    ProfileMessage.INVALID_EMAIL -> R.string.auth_email_invalid
    ProfileMessage.WEAK_PASSWORD -> R.string.auth_password_too_short
    ProfileMessage.EMAIL_ALREADY_IN_USE -> R.string.auth_email_already_in_use
    ProfileMessage.INVALID_CREDENTIALS -> R.string.auth_invalid_credentials
    ProfileMessage.GOOGLE_NO_CREDENTIAL -> R.string.auth_google_no_credential
    ProfileMessage.GOOGLE_CONFIGURATION_ERROR -> R.string.auth_google_configuration_error
    ProfileMessage.GOOGLE_INVALID_CREDENTIAL -> R.string.auth_google_invalid_credential
    ProfileMessage.GOOGLE_PROVIDER_UNAVAILABLE -> R.string.auth_google_provider_unavailable
    ProfileMessage.ACCOUNT_PROVIDER_CONFLICT -> R.string.auth_account_provider_conflict
    ProfileMessage.DISABLED_ACCOUNT -> R.string.auth_disabled_account
    ProfileMessage.TOO_MANY_REQUESTS -> R.string.auth_too_many_requests
    ProfileMessage.NETWORK_UNAVAILABLE -> R.string.auth_network_unavailable
    ProfileMessage.MISSING_CURRENT_USER -> R.string.auth_missing_current_user
    ProfileMessage.CREDENTIAL_STATE_CLEAR_FAILED ->
        R.string.auth_credential_state_clear_failed
    ProfileMessage.GENERIC_FAILURE -> R.string.auth_generic_failure
}

private fun ProfileMessage.isSuccess(): Boolean =
    this == ProfileMessage.VERIFICATION_EMAIL_SENT
