package com.kltn.travelassistant.feature.auth.domain

data class AuthUser(
    val uid: String,
    val email: String,
    val isEmailVerified: Boolean,
)

sealed interface AuthSession {
    data object Checking : AuthSession

    data object SignedOut : AuthSession

    data class VerificationRequired(val user: AuthUser) : AuthSession

    data class Authenticated(val user: AuthUser) : AuthSession

    data object Error : AuthSession
}

enum class AuthError {
    INVALID_EMAIL,
    WEAK_PASSWORD,
    EMAIL_ALREADY_IN_USE,
    INVALID_CREDENTIALS,
    DISABLED_ACCOUNT,
    TOO_MANY_REQUESTS,
    NETWORK_UNAVAILABLE,
    VERIFICATION_EMAIL_FAILED,
    MISSING_CURRENT_USER,
    UNKNOWN,
}

sealed interface AuthResult<out T> {
    data class Success<T>(val value: T) : AuthResult<T>

    data class Failure(val error: AuthError) : AuthResult<Nothing>
}

sealed interface RegistrationResult {
    data class Success(
        val user: AuthUser,
        val verificationEmailSent: Boolean,
        val verificationEmailError: AuthError? = null,
    ) : RegistrationResult

    data class Failure(val error: AuthError) : RegistrationResult
}
