package com.kltn.travelassistant.feature.auth.domain

import kotlinx.coroutines.flow.Flow

interface AuthRepository {
    fun observeSession(): Flow<AuthSession>

    suspend fun register(email: String, password: String): RegistrationResult

    suspend fun signIn(email: String, password: String): AuthResult<AuthUser>

    suspend fun signInWithGoogleIdToken(idToken: String): AuthResult<AuthUser>

    suspend fun refreshVerification(): AuthResult<AuthUser>

    suspend fun resendVerificationEmail(): AuthResult<Unit>

    suspend fun signOut(): AuthResult<Unit>
}
