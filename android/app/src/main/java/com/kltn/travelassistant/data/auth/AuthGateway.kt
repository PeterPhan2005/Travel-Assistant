package com.kltn.travelassistant.data.auth

import com.kltn.travelassistant.feature.auth.domain.AuthResult
import kotlinx.coroutines.flow.Flow

data class GatewayAuthUser(
    val uid: String,
    val email: String,
    val isEmailVerified: Boolean,
)

interface AuthGateway {
    fun observeCurrentUser(): Flow<GatewayAuthUser?>

    suspend fun createUser(email: String, password: String): AuthResult<GatewayAuthUser>

    suspend fun signIn(email: String, password: String): AuthResult<GatewayAuthUser>

    suspend fun reloadCurrentUser(): AuthResult<GatewayAuthUser>

    suspend fun sendVerificationEmail(): AuthResult<Unit>

    fun signOut(): AuthResult<Unit>
}
