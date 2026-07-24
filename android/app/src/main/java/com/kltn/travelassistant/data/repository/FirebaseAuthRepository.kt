package com.kltn.travelassistant.data.repository

import com.kltn.travelassistant.data.auth.AuthGateway
import com.kltn.travelassistant.data.auth.GatewayAuthUser
import com.kltn.travelassistant.feature.auth.domain.AuthRepository
import com.kltn.travelassistant.feature.auth.domain.AuthResult
import com.kltn.travelassistant.feature.auth.domain.AuthSession
import com.kltn.travelassistant.feature.auth.domain.AuthUser
import com.kltn.travelassistant.feature.auth.domain.RegistrationResult
import javax.inject.Inject
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.catch
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.flow.onStart

class FirebaseAuthRepository @Inject constructor(
    private val gateway: AuthGateway,
) : AuthRepository {
    override fun observeSession(): Flow<AuthSession> = gateway.observeCurrentUser()
        .map { user -> user.toSession() }
        .onStart { emit(AuthSession.Checking) }
        .catch { emit(AuthSession.Error) }

    override suspend fun register(
        email: String,
        password: String,
    ): RegistrationResult = when (val creation = gateway.createUser(email, password)) {
        is AuthResult.Failure -> RegistrationResult.Failure(creation.error)
        is AuthResult.Success -> {
            when (val delivery = gateway.sendVerificationEmail()) {
                is AuthResult.Success -> RegistrationResult.Success(
                    user = creation.value.toAuthUser(),
                    verificationEmailSent = true,
                )
                is AuthResult.Failure -> RegistrationResult.Success(
                    user = creation.value.toAuthUser(),
                    verificationEmailSent = false,
                    verificationEmailError = delivery.error,
                )
            }
        }
    }

    override suspend fun signIn(
        email: String,
        password: String,
    ): AuthResult<AuthUser> = when (val signIn = gateway.signIn(email, password)) {
        is AuthResult.Failure -> signIn
        is AuthResult.Success -> gateway.reloadCurrentUser().toDomainResult()
    }

    override suspend fun signInWithGoogleIdToken(
        idToken: String,
    ): AuthResult<AuthUser> = gateway.signInWithGoogleIdToken(idToken).toDomainResult()

    override suspend fun refreshVerification(): AuthResult<AuthUser> =
        gateway.reloadCurrentUser().toDomainResult()

    override suspend fun resendVerificationEmail(): AuthResult<Unit> =
        gateway.sendVerificationEmail()

    override suspend fun signOut(): AuthResult<Unit> = gateway.signOut()
}

private fun GatewayAuthUser?.toSession(): AuthSession {
    val user = this ?: return AuthSession.SignedOut
    if (user.uid.isBlank() || user.email.isBlank()) return AuthSession.Error
    val domainUser = user.toAuthUser()
    return if (domainUser.isEmailVerified) {
        AuthSession.Authenticated(domainUser)
    } else {
        AuthSession.VerificationRequired(domainUser)
    }
}

private fun GatewayAuthUser.toAuthUser(): AuthUser = AuthUser(
    uid = uid,
    email = email,
    isEmailVerified = isEmailVerified,
)

private fun AuthResult<GatewayAuthUser>.toDomainResult(): AuthResult<AuthUser> = when (this) {
    is AuthResult.Failure -> this
    is AuthResult.Success -> AuthResult.Success(value.toAuthUser())
}
