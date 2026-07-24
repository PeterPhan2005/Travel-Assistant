package com.kltn.travelassistant.data.repository

import com.kltn.travelassistant.data.auth.AuthGateway
import com.kltn.travelassistant.data.auth.GatewayAuthUser
import com.kltn.travelassistant.feature.auth.domain.AuthError
import com.kltn.travelassistant.feature.auth.domain.AuthResult
import com.kltn.travelassistant.feature.auth.domain.AuthSession
import com.kltn.travelassistant.feature.auth.domain.AuthUser
import com.kltn.travelassistant.feature.auth.domain.RegistrationResult
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.take
import kotlinx.coroutines.flow.toList
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import java.util.UUID

class FirebaseAuthRepositoryTest {
    @Test
    fun sessionObservationStartsCheckingAndMapsSignedOut() = runTest {
        val repository = FirebaseAuthRepository(FakeAuthGateway(initialUser = null))

        assertEquals(
            listOf(AuthSession.Checking, AuthSession.SignedOut),
            repository.observeSession().take(2).toList(),
        )
    }

    @Test
    fun restoredUsersMapToVerificationAwareSessionStates() = runTest {
        val unverifiedRepository = FirebaseAuthRepository(FakeAuthGateway(unverifiedGatewayUser))
        val verifiedRepository = FirebaseAuthRepository(FakeAuthGateway(verifiedGatewayUser))

        assertEquals(
            AuthSession.VerificationRequired(unverifiedUser),
            unverifiedRepository.observeSession().take(2).toList().last(),
        )
        assertEquals(
            AuthSession.Authenticated(verifiedUser),
            verifiedRepository.observeSession().take(2).toList().last(),
        )
    }

    @Test
    fun successfulRegistrationCreatesAccountThenRequestsVerificationEmail() = runTest {
        val gateway = FakeAuthGateway(
            createResult = AuthResult.Success(unverifiedGatewayUser),
        )
        val repository = FirebaseAuthRepository(gateway)

        val result = repository.register(email, password)

        assertEquals(
            RegistrationResult.Success(
                user = unverifiedUser,
                verificationEmailSent = true,
            ),
            result,
        )
        assertEquals(listOf("create", "sendVerification"), gateway.operations)
    }

    @Test
    fun verificationDeliveryFailureKeepsSuccessfulUnverifiedRegistration() = runTest {
        val gateway = FakeAuthGateway(
            createResult = AuthResult.Success(unverifiedGatewayUser),
            verificationResult = AuthResult.Failure(AuthError.NETWORK_UNAVAILABLE),
        )
        val repository = FirebaseAuthRepository(gateway)

        val result = repository.register(email, password)

        assertEquals(
            RegistrationResult.Success(
                user = unverifiedUser,
                verificationEmailSent = false,
                verificationEmailError = AuthError.NETWORK_UNAVAILABLE,
            ),
            result,
        )
        assertEquals(listOf("create", "sendVerification"), gateway.operations)
    }

    @Test
    fun verifiedSignInReloadsBeforeReturningAuthenticatedUser() = runTest {
        val gateway = FakeAuthGateway(
            signInResult = AuthResult.Success(unverifiedGatewayUser),
            reloadResults = ArrayDeque(listOf(AuthResult.Success(verifiedGatewayUser))),
        )
        val repository = FirebaseAuthRepository(gateway)

        assertEquals(AuthResult.Success(verifiedUser), repository.signIn(email, password))
        assertEquals(listOf("signIn", "reload"), gateway.operations)
    }

    @Test
    fun unverifiedSignInRemainsUnverifiedAfterReload() = runTest {
        val gateway = FakeAuthGateway(
            signInResult = AuthResult.Success(unverifiedGatewayUser),
            reloadResults = ArrayDeque(listOf(AuthResult.Success(unverifiedGatewayUser))),
        )
        val repository = FirebaseAuthRepository(gateway)

        assertEquals(AuthResult.Success(unverifiedUser), repository.signIn(email, password))
    }

    @Test
    fun googleCredentialExchangeMapsVerifiedAndUnexpectedlyUnverifiedUsers() = runTest {
        val verifiedGateway = FakeAuthGateway(
            googleSignInResult = AuthResult.Success(verifiedGatewayUser),
        )
        val unverifiedGateway = FakeAuthGateway(
            googleSignInResult = AuthResult.Success(unverifiedGatewayUser),
        )

        assertEquals(
            AuthResult.Success(verifiedUser),
            FirebaseAuthRepository(verifiedGateway)
                .signInWithGoogleIdToken(UUID.randomUUID().toString()),
        )
        assertEquals(
            AuthResult.Success(unverifiedUser),
            FirebaseAuthRepository(unverifiedGateway)
                .signInWithGoogleIdToken(UUID.randomUUID().toString()),
        )
        assertEquals(listOf("googleSignIn"), verifiedGateway.operations)
        assertEquals(listOf("googleSignIn"), unverifiedGateway.operations)
    }

    @Test
    fun googleCredentialFailuresRemainTypedAndSessionFlowStaysSourceOfTruth() = runTest {
        listOf(
            AuthError.INVALID_CREDENTIALS,
            AuthError.ACCOUNT_PROVIDER_CONFLICT,
            AuthError.NETWORK_UNAVAILABLE,
        ).forEach { error ->
            val gateway = FakeAuthGateway(
                initialUser = null,
                googleSignInResult = AuthResult.Failure(error),
            )
            val repository = FirebaseAuthRepository(gateway)

            assertEquals(
                AuthResult.Failure(error),
                repository.signInWithGoogleIdToken(UUID.randomUUID().toString()),
            )
            assertEquals(
                AuthSession.SignedOut,
                repository.observeSession().take(2).toList().last(),
            )
        }

        val gateway = FakeAuthGateway(
            initialUser = null,
            googleSignInResult = AuthResult.Success(verifiedGatewayUser),
        )
        val repository = FirebaseAuthRepository(gateway)
        assertEquals(
            AuthResult.Success(verifiedUser),
            repository.signInWithGoogleIdToken(UUID.randomUUID().toString()),
        )
        assertEquals(
            AuthSession.SignedOut,
            repository.observeSession().take(2).toList().last(),
        )
        gateway.emitCurrentUser(verifiedGatewayUser)
        assertEquals(
            AuthSession.Authenticated(verifiedUser),
            repository.observeSession().take(2).toList().last(),
        )
    }

    @Test
    fun refreshCanChangeUnverifiedUserToVerified() = runTest {
        val gateway = FakeAuthGateway(
            reloadResults = ArrayDeque(listOf(AuthResult.Success(verifiedGatewayUser))),
        )
        val repository = FirebaseAuthRepository(gateway)

        assertEquals(AuthResult.Success(verifiedUser), repository.refreshVerification())
    }

    @Test
    fun resendAndSignOutDelegateToGateway() = runTest {
        val gateway = FakeAuthGateway()
        val repository = FirebaseAuthRepository(gateway)

        assertEquals(AuthResult.Success(Unit), repository.resendVerificationEmail())
        assertEquals(AuthResult.Success(Unit), repository.signOut())
        assertEquals(listOf("sendVerification", "signOut"), gateway.operations)
    }

    @Test
    fun typedGatewayErrorsArePreservedWithoutExceptionText() = runTest {
        AuthError.entries.forEach { error ->
            val repository = FirebaseAuthRepository(
                FakeAuthGateway(signInResult = AuthResult.Failure(error)),
            )

            assertEquals(AuthResult.Failure(error), repository.signIn(email, password))
        }
    }

    @Test
    fun publicResultModelsContainNoPasswordOrTokenFields() {
        val fieldNames = listOf(
            AuthUser::class.java,
            RegistrationResult.Success::class.java,
        ).flatMap { type -> type.declaredFields.map { it.name.lowercase() } }

        assertFalse(fieldNames.any { it.contains("password") })
        assertFalse(fieldNames.any { it.contains("token") })
        assertTrue(fieldNames.contains("email"))
    }

    private class FakeAuthGateway(
        initialUser: GatewayAuthUser? = null,
        private val createResult: AuthResult<GatewayAuthUser> =
            AuthResult.Success(unverifiedGatewayUser),
        private val signInResult: AuthResult<GatewayAuthUser> =
            AuthResult.Success(unverifiedGatewayUser),
        private val googleSignInResult: AuthResult<GatewayAuthUser> =
            AuthResult.Success(verifiedGatewayUser),
        private val reloadResults: ArrayDeque<AuthResult<GatewayAuthUser>> =
            ArrayDeque(listOf(AuthResult.Success(unverifiedGatewayUser))),
        private val verificationResult: AuthResult<Unit> = AuthResult.Success(Unit),
        private val signOutResult: AuthResult<Unit> = AuthResult.Success(Unit),
    ) : AuthGateway {
        private val currentUser = MutableStateFlow(initialUser)
        val operations = mutableListOf<String>()

        override fun observeCurrentUser(): Flow<GatewayAuthUser?> = currentUser

        override suspend fun createUser(
            email: String,
            password: String,
        ): AuthResult<GatewayAuthUser> {
            operations += "create"
            return createResult
        }

        override suspend fun signIn(
            email: String,
            password: String,
        ): AuthResult<GatewayAuthUser> {
            operations += "signIn"
            return signInResult
        }

        override suspend fun signInWithGoogleIdToken(
            idToken: String,
        ): AuthResult<GatewayAuthUser> {
            operations += "googleSignIn"
            return googleSignInResult
        }

        fun emitCurrentUser(user: GatewayAuthUser?) {
            currentUser.value = user
        }

        override suspend fun reloadCurrentUser(): AuthResult<GatewayAuthUser> {
            operations += "reload"
            return reloadResults.removeFirst()
        }

        override suspend fun sendVerificationEmail(): AuthResult<Unit> {
            operations += "sendVerification"
            return verificationResult
        }

        override fun signOut(): AuthResult<Unit> {
            operations += "signOut"
            return signOutResult
        }
    }

    private companion object {
        const val email = "traveler@example.com"
        const val password = "secret1"
        val unverifiedGatewayUser = GatewayAuthUser("uid-1", email, false)
        val verifiedGatewayUser = unverifiedGatewayUser.copy(isEmailVerified = true)
        val unverifiedUser = AuthUser("uid-1", email, false)
        val verifiedUser = unverifiedUser.copy(isEmailVerified = true)
    }
}
