package com.kltn.travelassistant.feature.auth.presentation

import com.kltn.travelassistant.data.auth.CredentialStateClearer
import com.kltn.travelassistant.feature.auth.domain.AuthError
import com.kltn.travelassistant.feature.auth.domain.AuthRepository
import com.kltn.travelassistant.feature.auth.domain.AuthResult
import com.kltn.travelassistant.feature.auth.domain.AuthSession
import com.kltn.travelassistant.feature.auth.domain.AuthUser
import com.kltn.travelassistant.feature.auth.domain.CredentialStateClearResult
import com.kltn.travelassistant.feature.auth.domain.EmailValidationError
import com.kltn.travelassistant.feature.auth.domain.PasswordConfirmationValidationError
import com.kltn.travelassistant.feature.auth.domain.PasswordValidationError
import com.kltn.travelassistant.feature.auth.domain.RegistrationResult
import com.kltn.travelassistant.feature.auth.domain.GoogleSignInFailure
import com.kltn.travelassistant.feature.auth.domain.GoogleSignInResult
import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.advanceUntilIdle
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.runCurrent
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.test.setMain
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Before
import org.junit.Test

@OptIn(ExperimentalCoroutinesApi::class)
class ProfileViewModelTest {
    private val dispatcher = StandardTestDispatcher()

    @Before
    fun setUp() {
        Dispatchers.setMain(dispatcher)
    }

    @After
    fun tearDown() {
        Dispatchers.resetMain()
    }

    @Test
    fun initialStateIsCheckingThenRepositorySessionIsObserved() = runTest(dispatcher) {
        val repository = FakeAuthRepository(AuthSession.SignedOut)
        val viewModel = createViewModel(repository)

        assertEquals(AuthSession.Checking, viewModel.uiState.value.session)
        runCurrent()
        assertEquals(AuthSession.SignedOut, viewModel.uiState.value.session)

        repository.emitSession(AuthSession.VerificationRequired(unverifiedUser))
        runCurrent()
        assertEquals(
            AuthSession.VerificationRequired(unverifiedUser),
            viewModel.uiState.value.session,
        )
    }

    @Test
    fun switchingModesClearsPasswordAndValidationState() = runTest(dispatcher) {
        val viewModel = createViewModel(FakeAuthRepository())
        viewModel.onPasswordChanged("secret1")
        viewModel.onFormModeChanged(AuthFormMode.SIGN_UP)
        viewModel.submit()

        assertEquals(AuthFormMode.SIGN_UP, viewModel.uiState.value.formMode)
        assertEquals(EmailValidationError.REQUIRED, viewModel.uiState.value.emailError)
        assertEquals(PasswordValidationError.REQUIRED, viewModel.uiState.value.passwordError)
        assertEquals(
            PasswordConfirmationValidationError.REQUIRED,
            viewModel.uiState.value.passwordConfirmationError,
        )
    }

    @Test
    fun localValidationPreventsRepositoryCalls() = runTest(dispatcher) {
        val repository = FakeAuthRepository()
        val viewModel = createViewModel(repository)
        viewModel.onEmailChanged("bad-email")
        viewModel.onPasswordChanged("123")

        viewModel.submit()
        advanceUntilIdle()

        assertEquals(EmailValidationError.MALFORMED, viewModel.uiState.value.emailError)
        assertEquals(PasswordValidationError.TOO_SHORT, viewModel.uiState.value.passwordError)
        assertEquals(0, repository.signInCount)
        assertFalse(viewModel.uiState.value.isLoading)
    }

    @Test
    fun loadingPreventsDuplicateSubmission() = runTest(dispatcher) {
        val pendingSignIn = CompletableDeferred<AuthResult<AuthUser>>()
        val repository = FakeAuthRepository(
            signInBlock = { _, _ -> pendingSignIn.await() },
        )
        val viewModel = validSignInViewModel(repository)

        viewModel.submit()
        runCurrent()
        viewModel.submit()
        runCurrent()

        assertEquals(AuthOperation.SIGN_IN, viewModel.uiState.value.activeOperation)
        assertEquals(1, repository.signInCount)

        pendingSignIn.complete(AuthResult.Success(verifiedUser))
        advanceUntilIdle()
        assertEquals(AuthSession.Authenticated(verifiedUser), viewModel.uiState.value.session)
        assertFalse(viewModel.uiState.value.isLoading)
    }

    @Test
    fun registrationReachesVerificationRequiredAndReportsDelivery() = runTest(dispatcher) {
        val repository = FakeAuthRepository(
            registrationResult = RegistrationResult.Success(
                unverifiedUser,
                verificationEmailSent = true,
            ),
        )
        val viewModel = validRegistrationViewModel(repository)

        viewModel.submit()
        advanceUntilIdle()

        assertEquals(
            AuthSession.VerificationRequired(unverifiedUser),
            viewModel.uiState.value.session,
        )
        assertEquals(ProfileMessage.VERIFICATION_EMAIL_SENT, viewModel.uiState.value.message)
        assertEquals("traveler@example.com", repository.lastEmail)
        assertEquals("", viewModel.uiState.value.password)
    }

    @Test
    fun registrationDeliveryFailureKeepsVerificationSessionAndResendRecovery() =
        runTest(dispatcher) {
            val repository = FakeAuthRepository(
                registrationResult = RegistrationResult.Success(
                    unverifiedUser,
                    verificationEmailSent = false,
                    verificationEmailError = AuthError.NETWORK_UNAVAILABLE,
                ),
            )
            val viewModel = validRegistrationViewModel(repository)

            viewModel.submit()
            advanceUntilIdle()

            assertEquals(
                AuthSession.VerificationRequired(unverifiedUser),
                viewModel.uiState.value.session,
            )
            assertEquals(
                ProfileMessage.VERIFICATION_EMAIL_NOT_SENT,
                viewModel.uiState.value.message,
            )
        }

    @Test
    fun signInIsVerificationAwareForVerifiedAndUnverifiedUsers() = runTest(dispatcher) {
        val repository = FakeAuthRepository(signInResult = AuthResult.Success(verifiedUser))
        val viewModel = validSignInViewModel(repository)

        viewModel.submit()
        advanceUntilIdle()
        assertEquals(AuthSession.Authenticated(verifiedUser), viewModel.uiState.value.session)

        repository.signInResult = AuthResult.Success(unverifiedUser)
        viewModel.onPasswordChanged(password)
        viewModel.submit()
        advanceUntilIdle()
        assertEquals(
            AuthSession.VerificationRequired(unverifiedUser),
            viewModel.uiState.value.session,
        )
    }

    @Test
    fun googleSignInStartsOnlyExplicitlyAndSuppressesDuplicateAttempts() = runTest(dispatcher) {
        val repository = FakeAuthRepository()
        val viewModel = createViewModel(repository)
        runCurrent()

        assertNull(viewModel.uiState.value.activeOperation)
        val attemptId = viewModel.onGoogleSignInStarted()
        val duplicateAttempt = viewModel.onGoogleSignInStarted()

        assertEquals(1L, attemptId)
        assertNull(duplicateAttempt)
        assertEquals(AuthOperation.GOOGLE_SIGN_IN, viewModel.uiState.value.activeOperation)
        assertEquals(0, repository.googleSignInCount)
    }

    @Test
    fun googleSuccessIsVerificationAwareWithoutPuttingCredentialInUiState() = runTest(dispatcher) {
        val viewModel = createViewModel(FakeAuthRepository())
        runCurrent()

        val verifiedAttempt = checkNotNull(viewModel.onGoogleSignInStarted())
        viewModel.onGoogleSignInResult(
            verifiedAttempt,
            GoogleSignInResult.Success(verifiedUser),
        )
        assertEquals(AuthSession.Authenticated(verifiedUser), viewModel.uiState.value.session)

        val signedOutRepository = FakeAuthRepository(AuthSession.SignedOut)
        val unverifiedViewModel = createViewModel(signedOutRepository)
        runCurrent()
        val unverifiedAttempt = checkNotNull(unverifiedViewModel.onGoogleSignInStarted())
        unverifiedViewModel.onGoogleSignInResult(
            unverifiedAttempt,
            GoogleSignInResult.Success(unverifiedUser),
        )
        assertEquals(
            AuthSession.VerificationRequired(unverifiedUser),
            unverifiedViewModel.uiState.value.session,
        )

        val uiFieldNames = ProfileUiState::class.java.declaredFields.map { it.name.lowercase() }
        assertFalse(uiFieldNames.any { it.contains("token") || it.contains("credential") })
    }

    @Test
    fun googleCancellationIsHarmlessAndAllowsExplicitRetry() = runTest(dispatcher) {
        val viewModel = createViewModel(FakeAuthRepository())
        runCurrent()

        val firstAttempt = checkNotNull(viewModel.onGoogleSignInStarted())
        viewModel.onGoogleSignInResult(firstAttempt, GoogleSignInResult.Cancelled)

        assertEquals(AuthSession.SignedOut, viewModel.uiState.value.session)
        assertNull(viewModel.uiState.value.message)
        assertFalse(viewModel.uiState.value.isLoading)
        assertEquals(2L, viewModel.onGoogleSignInStarted())
    }

    @Test
    fun googleFailuresAreFriendlyAndRetryableWhileStaleResultsAreIgnored() =
        runTest(dispatcher) {
            val cases = mapOf(
                GoogleSignInFailure.NO_CREDENTIAL to ProfileMessage.GOOGLE_NO_CREDENTIAL,
                GoogleSignInFailure.INVALID_CREDENTIAL to
                    ProfileMessage.GOOGLE_INVALID_CREDENTIAL,
                GoogleSignInFailure.NETWORK_UNAVAILABLE to
                    ProfileMessage.NETWORK_UNAVAILABLE,
                GoogleSignInFailure.ACCOUNT_PROVIDER_CONFLICT to
                    ProfileMessage.ACCOUNT_PROVIDER_CONFLICT,
            )

            cases.forEach { (failure, message) ->
                val viewModel = createViewModel(FakeAuthRepository())
                runCurrent()
                val attempt = checkNotNull(viewModel.onGoogleSignInStarted())
                viewModel.onGoogleSignInResult(
                    attempt,
                    GoogleSignInResult.Failure(failure),
                )
                assertEquals(message, viewModel.uiState.value.message)
                assertFalse(viewModel.uiState.value.isLoading)
                assertEquals(attempt + 1, viewModel.onGoogleSignInStarted())
            }

            val viewModel = createViewModel(FakeAuthRepository())
            runCurrent()
            val oldAttempt = checkNotNull(viewModel.onGoogleSignInStarted())
            viewModel.onGoogleSignInResult(oldAttempt, GoogleSignInResult.Cancelled)
            val currentAttempt = checkNotNull(viewModel.onGoogleSignInStarted())
            viewModel.onGoogleSignInResult(
                oldAttempt,
                GoogleSignInResult.Success(verifiedUser),
            )
            assertEquals(AuthOperation.GOOGLE_SIGN_IN, viewModel.uiState.value.activeOperation)
            viewModel.onGoogleSignInResult(currentAttempt, GoogleSignInResult.Cancelled)
            assertEquals(AuthSession.SignedOut, viewModel.uiState.value.session)
        }

    @Test
    fun resendSuccessAndFailureAreRecoverable() = runTest(dispatcher) {
        val repository = FakeAuthRepository(AuthSession.VerificationRequired(unverifiedUser))
        val viewModel = createViewModel(repository)
        runCurrent()

        viewModel.resendVerificationEmail()
        advanceUntilIdle()
        assertEquals(ProfileMessage.VERIFICATION_EMAIL_SENT, viewModel.uiState.value.message)

        repository.resendResult = AuthResult.Failure(AuthError.NETWORK_UNAVAILABLE)
        viewModel.resendVerificationEmail()
        advanceUntilIdle()
        assertEquals(ProfileMessage.NETWORK_UNAVAILABLE, viewModel.uiState.value.message)
        assertEquals(2, repository.resendCount)
    }

    @Test
    fun verificationRefreshHandlesStillUnverifiedThenVerified() = runTest(dispatcher) {
        val repository = FakeAuthRepository(
            initialSession = AuthSession.VerificationRequired(unverifiedUser),
            refreshResult = AuthResult.Success(unverifiedUser),
        )
        val viewModel = createViewModel(repository)
        runCurrent()

        viewModel.refreshVerification()
        advanceUntilIdle()
        assertEquals(
            AuthSession.VerificationRequired(unverifiedUser),
            viewModel.uiState.value.session,
        )
        assertEquals(
            ProfileMessage.VERIFICATION_STILL_REQUIRED,
            viewModel.uiState.value.message,
        )

        repository.refreshResult = AuthResult.Success(verifiedUser)
        viewModel.refreshVerification()
        advanceUntilIdle()
        assertEquals(AuthSession.Authenticated(verifiedUser), viewModel.uiState.value.session)
        assertNull(viewModel.uiState.value.message)
    }

    @Test
    fun signOutTransitionsToSignedOutAndClearsPasswordFields() = runTest(dispatcher) {
        val repository = FakeAuthRepository(AuthSession.Authenticated(verifiedUser))
        val credentialStateClearer = FakeCredentialStateClearer()
        val viewModel = ProfileViewModel(repository, credentialStateClearer)
        runCurrent()
        viewModel.onPasswordChanged(password)

        viewModel.signOut()
        advanceUntilIdle()

        assertEquals(AuthSession.SignedOut, viewModel.uiState.value.session)
        assertEquals("", viewModel.uiState.value.password)
        assertEquals(1, repository.signOutCount)
        assertEquals(1, credentialStateClearer.clearCount)
    }

    @Test
    fun credentialStateClearFailureKeepsFirebaseSignedOutWithRecoverableWarning() =
        runTest(dispatcher) {
            val repository = FakeAuthRepository(AuthSession.Authenticated(verifiedUser))
            val credentialStateClearer = FakeCredentialStateClearer(
                result = CredentialStateClearResult.Failure,
            )
            val viewModel = ProfileViewModel(repository, credentialStateClearer)
            runCurrent()

            viewModel.signOut()
            advanceUntilIdle()

            assertEquals(AuthSession.SignedOut, viewModel.uiState.value.session)
            assertEquals(
                ProfileMessage.CREDENTIAL_STATE_CLEAR_FAILED,
                viewModel.uiState.value.message,
            )
            assertEquals(1, repository.signOutCount)
            assertEquals(1, credentialStateClearer.clearCount)
    }

    @Test
    fun neutralCredentialErrorAndInputEditingClearTransientFailure() = runTest(dispatcher) {
        val repository = FakeAuthRepository(
            signInResult = AuthResult.Failure(AuthError.INVALID_CREDENTIALS),
        )
        val viewModel = validSignInViewModel(repository)

        viewModel.submit()
        advanceUntilIdle()
        assertEquals(ProfileMessage.INVALID_CREDENTIALS, viewModel.uiState.value.message)

        viewModel.onPasswordChanged("new-password")
        assertNull(viewModel.uiState.value.message)
        assertNull(viewModel.uiState.value.passwordError)
    }

    @Test
    fun exposedStateIsReadOnly() = runTest(dispatcher) {
        val viewModel = createViewModel(FakeAuthRepository())

        assertFalse(viewModel.uiState is MutableStateFlow<*>)
    }

    private fun validSignInViewModel(repository: FakeAuthRepository): ProfileViewModel =
        createViewModel(repository).also { viewModel ->
            viewModel.onEmailChanged(" traveler@example.com ")
            viewModel.onPasswordChanged(password)
        }

    private fun validRegistrationViewModel(repository: FakeAuthRepository): ProfileViewModel =
        createViewModel(repository).also { viewModel ->
            viewModel.onFormModeChanged(AuthFormMode.SIGN_UP)
            viewModel.onEmailChanged(" traveler@example.com ")
            viewModel.onPasswordChanged(password)
            viewModel.onPasswordConfirmationChanged(password)
        }

    private fun createViewModel(
        repository: FakeAuthRepository,
        credentialStateClearer: CredentialStateClearer = FakeCredentialStateClearer(),
    ): ProfileViewModel = ProfileViewModel(repository, credentialStateClearer)

    private class FakeAuthRepository(
        initialSession: AuthSession = AuthSession.SignedOut,
        var registrationResult: RegistrationResult = RegistrationResult.Success(
            unverifiedUser,
            verificationEmailSent = true,
        ),
        var signInResult: AuthResult<AuthUser> = AuthResult.Success(verifiedUser),
        var refreshResult: AuthResult<AuthUser> = AuthResult.Success(verifiedUser),
        var resendResult: AuthResult<Unit> = AuthResult.Success(Unit),
        var signOutResult: AuthResult<Unit> = AuthResult.Success(Unit),
        var googleSignInResult: AuthResult<AuthUser> = AuthResult.Success(verifiedUser),
        private val signInBlock: (suspend (String, String) -> AuthResult<AuthUser>)? = null,
    ) : AuthRepository {
        private val sessions = MutableStateFlow(initialSession)
        var signInCount = 0
        var resendCount = 0
        var signOutCount = 0
        var googleSignInCount = 0
        var lastEmail: String? = null

        override fun observeSession(): Flow<AuthSession> = sessions

        fun emitSession(session: AuthSession) {
            sessions.value = session
        }

        override suspend fun register(email: String, password: String): RegistrationResult {
            lastEmail = email
            return registrationResult
        }

        override suspend fun signIn(email: String, password: String): AuthResult<AuthUser> {
            signInCount += 1
            lastEmail = email
            return signInBlock?.invoke(email, password) ?: signInResult
        }

        override suspend fun signInWithGoogleIdToken(
            idToken: String,
        ): AuthResult<AuthUser> {
            googleSignInCount += 1
            return googleSignInResult
        }

        override suspend fun refreshVerification(): AuthResult<AuthUser> = refreshResult

        override suspend fun resendVerificationEmail(): AuthResult<Unit> {
            resendCount += 1
            return resendResult
        }

        override suspend fun signOut(): AuthResult<Unit> {
            signOutCount += 1
            return signOutResult
        }
    }

    private class FakeCredentialStateClearer(
        private val result: CredentialStateClearResult = CredentialStateClearResult.Success,
    ) : CredentialStateClearer {
        var clearCount = 0

        override suspend fun clearCredentialState(): CredentialStateClearResult {
            clearCount += 1
            return result
        }
    }

    private companion object {
        const val password = "secret1"
        val unverifiedUser = AuthUser("uid-1", "traveler@example.com", false)
        val verifiedUser = unverifiedUser.copy(isEmailVerified = true)
    }
}
