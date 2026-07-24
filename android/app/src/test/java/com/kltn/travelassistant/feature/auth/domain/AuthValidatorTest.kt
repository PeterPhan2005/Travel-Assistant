package com.kltn.travelassistant.feature.auth.domain

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class AuthValidatorTest {
    @Test
    fun blankEmailIsRejectedAfterTrimming() {
        val result = AuthValidator.validateSignIn("   ", validPassword)

        assertEquals("", result.normalizedEmail)
        assertEquals(EmailValidationError.REQUIRED, result.emailError)
        assertFalse(result.isValid)
    }

    @Test
    fun clearlyMalformedEmailIsRejected() {
        listOf(
            "traveler",
            "traveler@",
            "@example.com",
            "traveler@example",
            ".traveler@example.com",
            "traveler..one@example.com",
        ).forEach { email ->
            assertEquals(
                EmailValidationError.MALFORMED,
                AuthValidator.validateSignIn(email, validPassword).emailError,
            )
        }
    }

    @Test
    fun validEmailIsTrimmedAndAccepted() {
        val result = AuthValidator.validateSignIn(" traveler@example.com ", validPassword)

        assertEquals("traveler@example.com", result.normalizedEmail)
        assertNull(result.emailError)
        assertTrue(result.isValid)
    }

    @Test
    fun blankPasswordIsRejected() {
        val result = AuthValidator.validateSignIn(validEmail, "")

        assertEquals(PasswordValidationError.REQUIRED, result.passwordError)
        assertFalse(result.isValid)
    }

    @Test
    fun passwordShorterThanFirebaseBaselineIsRejected() {
        val result = AuthValidator.validateSignIn(validEmail, "12345")

        assertEquals(PasswordValidationError.TOO_SHORT, result.passwordError)
        assertFalse(result.isValid)
    }

    @Test
    fun mismatchedConfirmationIsRejected() {
        val result = AuthValidator.validateRegistration(
            validEmail,
            validPassword,
            "different",
        )

        assertEquals(
            PasswordConfirmationValidationError.DOES_NOT_MATCH,
            result.passwordConfirmationError,
        )
        assertFalse(result.isValid)
    }

    @Test
    fun passwordCharactersAreNotSilentlyTrimmed() {
        val passwordWithSpaces = " secret "
        val matching = AuthValidator.validateRegistration(
            validEmail,
            passwordWithSpaces,
            passwordWithSpaces,
        )
        val trimmedConfirmation = AuthValidator.validateRegistration(
            validEmail,
            passwordWithSpaces,
            passwordWithSpaces.trim(),
        )

        assertTrue(matching.isValid)
        assertEquals(
            PasswordConfirmationValidationError.DOES_NOT_MATCH,
            trimmedConfirmation.passwordConfirmationError,
        )
    }

    private companion object {
        const val validEmail = "traveler@example.com"
        const val validPassword = "secret1"
    }
}
