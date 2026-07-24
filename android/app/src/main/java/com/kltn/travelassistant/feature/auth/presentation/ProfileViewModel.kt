package com.kltn.travelassistant.feature.auth.presentation

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.kltn.travelassistant.feature.auth.domain.AuthError
import com.kltn.travelassistant.feature.auth.domain.AuthRepository
import com.kltn.travelassistant.feature.auth.domain.AuthResult
import com.kltn.travelassistant.feature.auth.domain.AuthSession
import com.kltn.travelassistant.feature.auth.domain.AuthUser
import com.kltn.travelassistant.feature.auth.domain.AuthValidator
import com.kltn.travelassistant.feature.auth.domain.RegistrationResult
import dagger.hilt.android.lifecycle.HiltViewModel
import javax.inject.Inject
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Job
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.catch
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

@HiltViewModel
class ProfileViewModel @Inject constructor(
    private val authRepository: AuthRepository,
) : ViewModel() {
    private val mutableUiState = MutableStateFlow(ProfileUiState())
    val uiState: StateFlow<ProfileUiState> = mutableUiState.asStateFlow()

    private var sessionObservationJob: Job? = null

    init {
        observeSession()
    }

    fun onFormModeChanged(formMode: AuthFormMode) {
        if (mutableUiState.value.isLoading || mutableUiState.value.formMode == formMode) return
        mutableUiState.update { state ->
            state.copy(
                formMode = formMode,
                password = "",
                passwordConfirmation = "",
                emailError = null,
                passwordError = null,
                passwordConfirmationError = null,
                message = null,
            )
        }
    }

    fun onEmailChanged(email: String) {
        mutableUiState.update { state ->
            state.copy(email = email, emailError = null, message = null)
        }
    }

    fun onPasswordChanged(password: String) {
        mutableUiState.update { state ->
            state.copy(password = password, passwordError = null, message = null)
        }
    }

    fun onPasswordConfirmationChanged(passwordConfirmation: String) {
        mutableUiState.update { state ->
            state.copy(
                passwordConfirmation = passwordConfirmation,
                passwordConfirmationError = null,
                message = null,
            )
        }
    }

    fun submit() {
        if (mutableUiState.value.isLoading) return
        when (mutableUiState.value.formMode) {
            AuthFormMode.SIGN_IN -> signIn()
            AuthFormMode.SIGN_UP -> register()
        }
    }

    fun refreshVerification() {
        launchOperation(AuthOperation.REFRESH_VERIFICATION) {
            when (val result = safely { authRepository.refreshVerification() }) {
                is AuthResult.Failure -> showFailure(result.error)
                is AuthResult.Success -> {
                    val session = result.value.toSession()
                    mutableUiState.update { state ->
                        state.copy(
                            session = session,
                            message = if (session is AuthSession.VerificationRequired) {
                                ProfileMessage.VERIFICATION_STILL_REQUIRED
                            } else {
                                null
                            },
                        )
                    }
                }
            }
        }
    }

    fun resendVerificationEmail() {
        launchOperation(AuthOperation.RESEND_VERIFICATION) {
            when (val result = safelyUnit { authRepository.resendVerificationEmail() }) {
                is AuthResult.Failure -> showFailure(result.error)
                is AuthResult.Success -> mutableUiState.update { state ->
                    state.copy(message = ProfileMessage.VERIFICATION_EMAIL_SENT)
                }
            }
        }
    }

    fun signOut() {
        launchOperation(AuthOperation.SIGN_OUT) {
            when (val result = safelyUnit { authRepository.signOut() }) {
                is AuthResult.Failure -> showFailure(result.error)
                is AuthResult.Success -> mutableUiState.update { state ->
                    state.copy(
                        session = AuthSession.SignedOut,
                        password = "",
                        passwordConfirmation = "",
                        message = null,
                    )
                }
            }
        }
    }

    fun retrySessionObservation() {
        if (mutableUiState.value.isLoading) return
        mutableUiState.update { state ->
            state.copy(session = AuthSession.Checking, message = null)
        }
        observeSession()
    }

    private fun observeSession() {
        sessionObservationJob?.cancel()
        sessionObservationJob = viewModelScope.launch {
            authRepository.observeSession()
                .catch { emit(AuthSession.Error) }
                .collect { session ->
                    mutableUiState.update { state -> state.copy(session = session) }
                }
        }
    }

    private fun signIn() {
        val state = mutableUiState.value
        val validation = AuthValidator.validateSignIn(state.email, state.password)
        if (!validation.isValid) {
            mutableUiState.update {
                it.copy(
                    emailError = validation.emailError,
                    passwordError = validation.passwordError,
                    passwordConfirmationError = null,
                    message = null,
                )
            }
            return
        }
        mutableUiState.update { it.copy(email = validation.normalizedEmail) }
        launchOperation(AuthOperation.SIGN_IN) {
            when (
                val result = safely {
                    authRepository.signIn(validation.normalizedEmail, state.password)
                }
            ) {
                is AuthResult.Failure -> showFailure(result.error)
                is AuthResult.Success -> mutableUiState.update { current ->
                    current.copy(
                        session = result.value.toSession(),
                        password = "",
                        passwordConfirmation = "",
                        message = null,
                    )
                }
            }
        }
    }

    private fun register() {
        val state = mutableUiState.value
        val validation = AuthValidator.validateRegistration(
            email = state.email,
            password = state.password,
            passwordConfirmation = state.passwordConfirmation,
        )
        if (!validation.isValid) {
            mutableUiState.update {
                it.copy(
                    emailError = validation.emailError,
                    passwordError = validation.passwordError,
                    passwordConfirmationError = validation.passwordConfirmationError,
                    message = null,
                )
            }
            return
        }
        mutableUiState.update { it.copy(email = validation.normalizedEmail) }
        launchOperation(AuthOperation.SIGN_UP) {
            when (
                val result = safelyRegistration {
                    authRepository.register(validation.normalizedEmail, state.password)
                }
            ) {
                is RegistrationResult.Failure -> showFailure(result.error)
                is RegistrationResult.Success -> mutableUiState.update { current ->
                    current.copy(
                        session = result.user.toSession(),
                        password = "",
                        passwordConfirmation = "",
                        message = if (result.verificationEmailSent) {
                            ProfileMessage.VERIFICATION_EMAIL_SENT
                        } else {
                            ProfileMessage.VERIFICATION_EMAIL_NOT_SENT
                        },
                    )
                }
            }
        }
    }

    private fun launchOperation(
        operation: AuthOperation,
        block: suspend () -> Unit,
    ) {
        if (mutableUiState.value.isLoading) return
        mutableUiState.update { state ->
            state.copy(activeOperation = operation, message = null)
        }
        viewModelScope.launch {
            try {
                block()
            } finally {
                mutableUiState.update { state -> state.copy(activeOperation = null) }
            }
        }
    }

    private fun showFailure(error: AuthError) {
        mutableUiState.update { state -> state.copy(message = error.toProfileMessage()) }
    }

    private suspend fun safely(
        block: suspend () -> AuthResult<AuthUser>,
    ): AuthResult<AuthUser> = try {
        block()
    } catch (exception: CancellationException) {
        throw exception
    } catch (_: Exception) {
        AuthResult.Failure(AuthError.UNKNOWN)
    }

    private suspend fun safelyUnit(
        block: suspend () -> AuthResult<Unit>,
    ): AuthResult<Unit> = try {
        block()
    } catch (exception: CancellationException) {
        throw exception
    } catch (_: Exception) {
        AuthResult.Failure(AuthError.UNKNOWN)
    }

    private suspend fun safelyRegistration(
        block: suspend () -> RegistrationResult,
    ): RegistrationResult = try {
        block()
    } catch (exception: CancellationException) {
        throw exception
    } catch (_: Exception) {
        RegistrationResult.Failure(AuthError.UNKNOWN)
    }
}

private fun AuthUser.toSession(): AuthSession =
    if (isEmailVerified) {
        AuthSession.Authenticated(this)
    } else {
        AuthSession.VerificationRequired(this)
    }

private fun AuthError.toProfileMessage(): ProfileMessage = when (this) {
    AuthError.INVALID_EMAIL -> ProfileMessage.INVALID_EMAIL
    AuthError.WEAK_PASSWORD -> ProfileMessage.WEAK_PASSWORD
    AuthError.EMAIL_ALREADY_IN_USE -> ProfileMessage.EMAIL_ALREADY_IN_USE
    AuthError.INVALID_CREDENTIALS -> ProfileMessage.INVALID_CREDENTIALS
    AuthError.DISABLED_ACCOUNT -> ProfileMessage.DISABLED_ACCOUNT
    AuthError.TOO_MANY_REQUESTS -> ProfileMessage.TOO_MANY_REQUESTS
    AuthError.NETWORK_UNAVAILABLE -> ProfileMessage.NETWORK_UNAVAILABLE
    AuthError.VERIFICATION_EMAIL_FAILED -> ProfileMessage.VERIFICATION_EMAIL_NOT_SENT
    AuthError.MISSING_CURRENT_USER -> ProfileMessage.MISSING_CURRENT_USER
    AuthError.UNKNOWN -> ProfileMessage.GENERIC_FAILURE
}
