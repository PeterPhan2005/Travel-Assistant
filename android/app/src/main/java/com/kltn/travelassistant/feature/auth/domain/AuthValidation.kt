package com.kltn.travelassistant.feature.auth.domain

enum class EmailValidationError {
    REQUIRED,
    MALFORMED,
}

enum class PasswordValidationError {
    REQUIRED,
    TOO_SHORT,
}

enum class PasswordConfirmationValidationError {
    REQUIRED,
    DOES_NOT_MATCH,
}

data class AuthValidationResult(
    val normalizedEmail: String,
    val emailError: EmailValidationError? = null,
    val passwordError: PasswordValidationError? = null,
    val passwordConfirmationError: PasswordConfirmationValidationError? = null,
) {
    val isValid: Boolean
        get() = emailError == null &&
            passwordError == null &&
            passwordConfirmationError == null
}

object AuthValidator {
    const val MINIMUM_PASSWORD_LENGTH = 6

    private val emailPattern = Regex(
        pattern = "^[A-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?(?:\\.[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?)+$",
        option = RegexOption.IGNORE_CASE,
    )

    fun validateSignIn(email: String, password: String): AuthValidationResult =
        validate(email = email, password = password, passwordConfirmation = null)

    fun validateRegistration(
        email: String,
        password: String,
        passwordConfirmation: String,
    ): AuthValidationResult = validate(
        email = email,
        password = password,
        passwordConfirmation = passwordConfirmation,
    )

    private fun validate(
        email: String,
        password: String,
        passwordConfirmation: String?,
    ): AuthValidationResult {
        val normalizedEmail = email.trim()
        val emailError = when {
            normalizedEmail.isBlank() -> EmailValidationError.REQUIRED
            isClearlyMalformedEmail(normalizedEmail) -> EmailValidationError.MALFORMED
            else -> null
        }
        val passwordError = when {
            password.isEmpty() -> PasswordValidationError.REQUIRED
            password.length < MINIMUM_PASSWORD_LENGTH -> PasswordValidationError.TOO_SHORT
            else -> null
        }
        val confirmationError = when {
            passwordConfirmation == null -> null
            passwordConfirmation.isEmpty() -> PasswordConfirmationValidationError.REQUIRED
            passwordConfirmation != password -> PasswordConfirmationValidationError.DOES_NOT_MATCH
            else -> null
        }
        return AuthValidationResult(
            normalizedEmail = normalizedEmail,
            emailError = emailError,
            passwordError = passwordError,
            passwordConfirmationError = confirmationError,
        )
    }

    private fun isClearlyMalformedEmail(email: String): Boolean {
        if (!emailPattern.matches(email)) return true
        val localPart = email.substringBefore('@')
        return localPart.startsWith('.') ||
            localPart.endsWith('.') ||
            ".." in localPart
    }
}
