package com.kltn.travelassistant.feature.auth.presentation

import com.kltn.travelassistant.feature.auth.domain.AuthSession
import com.kltn.travelassistant.feature.auth.domain.EmailValidationError
import com.kltn.travelassistant.feature.auth.domain.PasswordConfirmationValidationError
import com.kltn.travelassistant.feature.auth.domain.PasswordValidationError

data class ProfileUiState(
    val session: AuthSession = AuthSession.Checking,
    val formMode: AuthFormMode = AuthFormMode.SIGN_IN,
    val email: String = "",
    val password: String = "",
    val passwordConfirmation: String = "",
    val emailError: EmailValidationError? = null,
    val passwordError: PasswordValidationError? = null,
    val passwordConfirmationError: PasswordConfirmationValidationError? = null,
    val activeOperation: AuthOperation? = null,
    val message: ProfileMessage? = null,
) {
    val isLoading: Boolean
        get() = activeOperation != null
}

enum class AuthFormMode {
    SIGN_IN,
    SIGN_UP,
}

enum class AuthOperation {
    SIGN_IN,
    GOOGLE_SIGN_IN,
    SIGN_UP,
    REFRESH_VERIFICATION,
    RESEND_VERIFICATION,
    SIGN_OUT,
}

enum class ProfileMessage {
    VERIFICATION_EMAIL_SENT,
    VERIFICATION_EMAIL_NOT_SENT,
    VERIFICATION_STILL_REQUIRED,
    INVALID_EMAIL,
    WEAK_PASSWORD,
    EMAIL_ALREADY_IN_USE,
    INVALID_CREDENTIALS,
    GOOGLE_NO_CREDENTIAL,
    GOOGLE_CONFIGURATION_ERROR,
    GOOGLE_INVALID_CREDENTIAL,
    GOOGLE_PROVIDER_UNAVAILABLE,
    ACCOUNT_PROVIDER_CONFLICT,
    DISABLED_ACCOUNT,
    TOO_MANY_REQUESTS,
    NETWORK_UNAVAILABLE,
    MISSING_CURRENT_USER,
    CREDENTIAL_STATE_CLEAR_FAILED,
    GENERIC_FAILURE,
}
