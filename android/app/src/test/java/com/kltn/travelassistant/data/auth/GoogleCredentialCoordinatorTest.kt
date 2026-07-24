package com.kltn.travelassistant.data.auth

import androidx.credentials.exceptions.GetCredentialCancellationException
import androidx.credentials.exceptions.GetCredentialProviderConfigurationException
import androidx.credentials.exceptions.GetCredentialUnsupportedException
import androidx.credentials.exceptions.NoCredentialException
import com.google.android.libraries.identity.googleid.GoogleIdTokenCredential
import com.kltn.travelassistant.feature.auth.domain.AuthError
import com.kltn.travelassistant.feature.auth.domain.AuthRepository
import com.kltn.travelassistant.feature.auth.domain.AuthResult
import com.kltn.travelassistant.feature.auth.domain.AuthSession
import com.kltn.travelassistant.feature.auth.domain.AuthUser
import com.kltn.travelassistant.feature.auth.domain.GoogleSignInFailure
import com.kltn.travelassistant.feature.auth.domain.GoogleSignInResult
import com.kltn.travelassistant.feature.auth.domain.RegistrationResult
import java.util.UUID
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flowOf
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertSame
import org.junit.Test

class GoogleCredentialCoordinatorTest {
    @Test
    fun validGoogleCredentialIsExchangedAndVerifiedUserIsReturned() = runTest {
        val repository = FakeAuthRepository(AuthResult.Success(verifiedUser))
        val coordinator = coordinator(repository)
        val ephemeralValue = UUID.randomUUID().toString()

        val result = coordinator.handleAcquisition(
            GoogleCredentialAcquisition.CredentialReceived(ephemeralValue),
        )

        assertEquals(GoogleSignInResult.Success(verifiedUser), result)
        assertEquals(1, repository.googleExchangeCount)
    }

    @Test
    fun cancellationAndCredentialFailuresRemainTypedWithoutFirebaseExchange() = runTest {
        val cases = mapOf(
            GoogleCredentialAcquisition.Cancelled to GoogleSignInResult.Cancelled,
            GoogleCredentialAcquisition.NoCredential to GoogleSignInResult.Failure(
                GoogleSignInFailure.NO_CREDENTIAL,
            ),
            GoogleCredentialAcquisition.ConfigurationError to GoogleSignInResult.Failure(
                GoogleSignInFailure.CONFIGURATION,
            ),
            GoogleCredentialAcquisition.InvalidCredential to GoogleSignInResult.Failure(
                GoogleSignInFailure.INVALID_CREDENTIAL,
            ),
            GoogleCredentialAcquisition.ProviderUnavailable to GoogleSignInResult.Failure(
                GoogleSignInFailure.PROVIDER_UNAVAILABLE,
            ),
            GoogleCredentialAcquisition.Failure to GoogleSignInResult.Failure(
                GoogleSignInFailure.UNKNOWN,
            ),
        )

        cases.forEach { (acquisition, expected) ->
            val repository = FakeAuthRepository()
            assertEquals(expected, coordinator(repository).handleAcquisition(acquisition))
            assertEquals(0, repository.googleExchangeCount)
        }
    }

    @Test
    fun firebaseFailuresMapToStableGoogleFailures() = runTest {
        val cases = mapOf(
            AuthError.INVALID_CREDENTIALS to GoogleSignInFailure.INVALID_CREDENTIAL,
            AuthError.ACCOUNT_PROVIDER_CONFLICT to
                GoogleSignInFailure.ACCOUNT_PROVIDER_CONFLICT,
            AuthError.DISABLED_ACCOUNT to GoogleSignInFailure.DISABLED_ACCOUNT,
            AuthError.TOO_MANY_REQUESTS to GoogleSignInFailure.TOO_MANY_REQUESTS,
            AuthError.NETWORK_UNAVAILABLE to GoogleSignInFailure.NETWORK_UNAVAILABLE,
            AuthError.UNKNOWN to GoogleSignInFailure.UNKNOWN,
        )

        cases.forEach { (error, expected) ->
            val coordinator = coordinator(
                FakeAuthRepository(AuthResult.Failure(error)),
            )
            val result = coordinator.handleAcquisition(
                GoogleCredentialAcquisition.CredentialReceived(UUID.randomUUID().toString()),
            )
            assertEquals(GoogleSignInResult.Failure(expected), result)
        }
    }

    @Test
    fun acquisitionEngineAcceptsOnlyGoogleIdCredentialsAndControlsParsingFailures() = runTest {
        val ephemeralValue = UUID.randomUUID().toString()
        val parser = FakeGoogleIdTokenParser(result = ephemeralValue)
        val engine = engine(clientId = "configured-at-runtime", parser = parser)
        val payload = Any()

        val received = engine.acquireWith {
            CredentialEnvelope.Custom(
                type = GoogleIdTokenCredential.TYPE_GOOGLE_ID_TOKEN_CREDENTIAL,
                payload = payload,
            )
        }
        assertEquals(ephemeralValue, received.requireReceivedValue())
        assertSame(payload, parser.lastPayload)

        val unsupportedType = engine.acquireWith {
            CredentialEnvelope.Custom(type = "unsupported-type", payload = payload)
        }
        assertEquals(GoogleCredentialAcquisition.InvalidCredential, unsupportedType)

        val unsupportedCredential = engine.acquireWith { CredentialEnvelope.Unsupported }
        assertEquals(GoogleCredentialAcquisition.InvalidCredential, unsupportedCredential)

        parser.failure = IllegalArgumentException()
        val malformed = engine.acquireWith {
            CredentialEnvelope.Custom(
                type = GoogleIdTokenCredential.TYPE_GOOGLE_ID_TOKEN_CREDENTIAL,
                payload = payload,
            )
        }
        assertEquals(GoogleCredentialAcquisition.InvalidCredential, malformed)
    }

    @Test
    fun acquisitionEngineHandlesMissingConfigurationCancellationAndProviderFailures() = runTest {
        listOf(null, "", "   ").forEach { clientId ->
            val result = engine(clientId = clientId).acquireWith {
                throw AssertionError("Credential request must not start")
            }
            assertEquals(GoogleCredentialAcquisition.ConfigurationError, result)
        }

        val engine = engine(clientId = "configured-at-runtime")
        assertEquals(
            GoogleCredentialAcquisition.Cancelled,
            engine.acquireWith { throw GetCredentialCancellationException() },
        )
        assertEquals(
            GoogleCredentialAcquisition.NoCredential,
            engine.acquireWith { throw NoCredentialException() },
        )
        assertEquals(
            GoogleCredentialAcquisition.ProviderUnavailable,
            engine.acquireWith { throw GetCredentialProviderConfigurationException() },
        )
        assertEquals(
            GoogleCredentialAcquisition.ProviderUnavailable,
            engine.acquireWith { throw GetCredentialUnsupportedException() },
        )
        assertEquals(
            GoogleCredentialAcquisition.Failure,
            engine.acquireWith { throw IllegalStateException() },
        )
    }

    @Test
    fun publicResultsAndDescriptionsDoNotExposeCredentialValues() {
        val ephemeralValue = UUID.randomUUID().toString()
        val acquisition = GoogleCredentialAcquisition.CredentialReceived(ephemeralValue)
        val envelope = CredentialEnvelope.Custom(
            type = GoogleIdTokenCredential.TYPE_GOOGLE_ID_TOKEN_CREDENTIAL,
            payload = ephemeralValue,
        )
        val publicFieldNames = listOf(
            GoogleSignInResult.Success::class.java,
            GoogleSignInResult.Failure::class.java,
            AuthUser::class.java,
        ).flatMap { type -> type.declaredFields.map { it.name.lowercase() } }

        assertFalse(publicFieldNames.any { it.contains("token") || it.contains("credential") })
        assertFalse(acquisition.toString().contains(ephemeralValue))
        assertFalse(envelope.toString().contains(ephemeralValue))
    }

    private fun coordinator(
        repository: FakeAuthRepository,
    ): DefaultGoogleCredentialCoordinator = DefaultGoogleCredentialCoordinator(
        credentialAcquirer = FakeGoogleCredentialAcquirer,
        authRepository = repository,
    )

    private fun engine(
        clientId: String?,
        parser: FakeGoogleIdTokenParser = FakeGoogleIdTokenParser(UUID.randomUUID().toString()),
    ): GoogleCredentialAcquisitionEngine = GoogleCredentialAcquisitionEngine(
        clientIdProvider = object : GoogleClientIdProvider {
            override fun getServerClientId(): String? = clientId
        },
        tokenParser = parser,
    )

    private fun GoogleCredentialAcquisition.requireReceivedValue(): String {
        check(this is GoogleCredentialAcquisition.CredentialReceived)
        return consumeIdToken()
    }

    private object FakeGoogleCredentialAcquirer : GoogleCredentialAcquirer {
        override suspend fun acquire(
            activity: android.app.Activity,
        ): GoogleCredentialAcquisition = error("Not used by this JVM test")

        override suspend fun clearCredentialState() =
            com.kltn.travelassistant.feature.auth.domain.CredentialStateClearResult.Success
    }

    private class FakeGoogleIdTokenParser(
        private val result: String,
        var failure: Exception? = null,
    ) : GoogleIdTokenParser {
        var lastPayload: Any? = null

        override fun parse(credential: CredentialEnvelope.Custom): String {
            lastPayload = credential.payload
            failure?.let { throw it }
            return result
        }
    }

    private class FakeAuthRepository(
        private val googleResult: AuthResult<AuthUser> = AuthResult.Success(verifiedUser),
    ) : AuthRepository {
        var googleExchangeCount = 0

        override fun observeSession(): Flow<AuthSession> = flowOf(AuthSession.SignedOut)

        override suspend fun register(
            email: String,
            password: String,
        ): RegistrationResult = error("Not used")

        override suspend fun signIn(
            email: String,
            password: String,
        ): AuthResult<AuthUser> = error("Not used")

        override suspend fun signInWithGoogleIdToken(idToken: String): AuthResult<AuthUser> {
            googleExchangeCount += 1
            return googleResult
        }

        override suspend fun refreshVerification(): AuthResult<AuthUser> = error("Not used")

        override suspend fun resendVerificationEmail(): AuthResult<Unit> = error("Not used")

        override suspend fun signOut(): AuthResult<Unit> = error("Not used")
    }

    private companion object {
        val verifiedUser = AuthUser(
            uid = "uid-private",
            email = "traveler@example.com",
            isEmailVerified = true,
        )
    }
}
