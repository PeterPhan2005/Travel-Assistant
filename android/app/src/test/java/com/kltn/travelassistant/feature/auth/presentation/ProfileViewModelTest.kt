package com.kltn.travelassistant.feature.auth.presentation

import com.kltn.travelassistant.feature.auth.domain.AuthError
import com.kltn.travelassistant.feature.auth.domain.AuthRepository
import com.kltn.travelassistant.feature.auth.domain.AuthResult
import com.kltn.travelassistant.feature.auth.domain.AuthSession
import com.kltn.travelassistant.feature.auth.domain.AuthUser
import com.kltn.travelassistant.feature.auth.domain.EmailValidationError
import com.kltn.travelassistant.feature.auth.domain.PasswordConfirmationValidationError
import com.kltn.travelassistant.feature.auth.domain.PasswordValidationError
import com.kltn.travelassistant.feature.auth.domain.RegistrationResult
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
        val viewModel = ProfileViewModel(repository)

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
        val viewModel = ProfileViewModel(FakeAuthRepository())
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
        val viewModel = ProfileViewModel(repository)
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
    fun resendSuccessAndFailureAreRecoverable() = runTest(dispatcher) {
        val repository = FakeAuthRepository(AuthSession.VerificationRequired(unverifiedUser))
        val viewModel = ProfileViewModel(repository)
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
        val viewModel = ProfileViewModel(repository)
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
        val viewModel = ProfileViewModel(repository)
        runCurrent()
        viewModel.onPasswordChanged(password)

        viewModel.signOut()
        advanceUntilIdle()

        assertEquals(AuthSession.SignedOut, viewModel.uiState.value.session)
        assertEquals("", viewModel.uiState.value.password)
        assertEquals(1, repository.signOutCount)
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
        val viewModel = ProfileViewModel(FakeAuthRepository())

        assertFalse(viewModel.uiState is MutableStateFlow<*>)
    }

    private fun validSignInViewModel(repository: FakeAuthRepository): ProfileViewModel =
        ProfileViewModel(repository).also { viewModel ->
            viewModel.onEmailChanged(" traveler@example.com ")
            viewModel.onPasswordChanged(password)
        }

    private fun validRegistrationViewModel(repository: FakeAuthRepository): ProfileViewModel =
        ProfileViewModel(repository).also { viewModel ->
            viewModel.onFormModeChanged(AuthFormMode.SIGN_UP)
            viewModel.onEmailChanged(" traveler@example.com ")
            viewModel.onPasswordChanged(password)
            viewModel.onPasswordConfirmationChanged(password)
        }

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
        private val signInBlock: (suspend (String, String) -> AuthResult<AuthUser>)? = null,
    ) : AuthRepository {
        private val sessions = MutableStateFlow(initialSession)
        var signInCount = 0
        var resendCount = 0
        var signOutCount = 0
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

    private companion object {
        const val password = "secret1"
        val unverifiedUser = AuthUser("uid-1", "traveler@example.com", false)
        val verifiedUser = unverifiedUser.copy(isEmailVerified = true)
    }
}
