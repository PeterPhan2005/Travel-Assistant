package com.kltn.travelassistant.data.auth

import com.kltn.travelassistant.feature.auth.domain.AuthError
import org.junit.Assert.assertEquals
import org.junit.Test

class FirebaseAuthErrorMapperTest {
    @Test
    fun commonFirebaseCodesMapToStableErrors() {
        val expectations = mapOf(
            "ERROR_INVALID_EMAIL" to AuthError.INVALID_EMAIL,
            "ERROR_WEAK_PASSWORD" to AuthError.WEAK_PASSWORD,
            "ERROR_EMAIL_ALREADY_IN_USE" to AuthError.EMAIL_ALREADY_IN_USE,
            "ERROR_ACCOUNT_EXISTS_WITH_DIFFERENT_CREDENTIAL" to
                AuthError.ACCOUNT_PROVIDER_CONFLICT,
            "ERROR_INVALID_CREDENTIAL" to AuthError.INVALID_CREDENTIALS,
            "ERROR_WRONG_PASSWORD" to AuthError.INVALID_CREDENTIALS,
            "ERROR_USER_NOT_FOUND" to AuthError.INVALID_CREDENTIALS,
            "ERROR_USER_DISABLED" to AuthError.DISABLED_ACCOUNT,
            "ERROR_TOO_MANY_REQUESTS" to AuthError.TOO_MANY_REQUESTS,
        )

        expectations.forEach { (code, expected) ->
            assertEquals(
                expected,
                FirebaseAuthErrorMapper.mapCode(code),
            )
        }
    }

    @Test
    fun networkAndVerificationFallbackRemainTyped() {
        assertEquals(
            AuthError.NETWORK_UNAVAILABLE,
            FirebaseAuthErrorMapper.mapCode("ERROR_NETWORK_REQUEST_FAILED"),
        )
        assertEquals(
            AuthError.VERIFICATION_EMAIL_FAILED,
            FirebaseAuthErrorMapper.mapCode(
                errorCode = "UNRECOGNIZED_DELIVERY_ERROR",
                fallback = AuthError.VERIFICATION_EMAIL_FAILED,
            ),
        )
    }
}
