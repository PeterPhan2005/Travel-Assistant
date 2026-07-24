package com.kltn.travelassistant.data.auth

import com.google.android.gms.tasks.Task
import com.google.firebase.FirebaseNetworkException
import com.google.firebase.FirebaseTooManyRequestsException
import com.google.firebase.auth.AuthResult as FirebaseSignInResult
import com.google.firebase.auth.FirebaseAuth
import com.google.firebase.auth.FirebaseAuthException
import com.google.firebase.auth.FirebaseUser
import com.kltn.travelassistant.feature.auth.domain.AuthError
import com.kltn.travelassistant.feature.auth.domain.AuthResult
import javax.inject.Inject
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.channels.awaitClose
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.callbackFlow
import kotlinx.coroutines.suspendCancellableCoroutine
import kotlin.coroutines.resume
import kotlin.coroutines.resumeWithException

class FirebaseAuthGateway @Inject constructor(
    private val firebaseAuth: FirebaseAuth,
) : AuthGateway {
    override fun observeCurrentUser(): Flow<GatewayAuthUser?> = callbackFlow {
        val listener = FirebaseAuth.AuthStateListener { auth ->
            trySend(auth.currentUser?.toGatewayUser())
        }
        try {
            firebaseAuth.addAuthStateListener(listener)
        } catch (exception: Exception) {
            close(exception)
        }
        awaitClose {
            firebaseAuth.removeAuthStateListener(listener)
        }
    }

    override suspend fun createUser(
        email: String,
        password: String,
    ): AuthResult<GatewayAuthUser> = runFirebaseCall {
        val result = firebaseAuth.createUserWithEmailAndPassword(email, password).await()
        result.requireUser()
    }

    override suspend fun signIn(
        email: String,
        password: String,
    ): AuthResult<GatewayAuthUser> = runFirebaseCall {
        val result = firebaseAuth.signInWithEmailAndPassword(email, password).await()
        result.requireUser()
    }

    override suspend fun reloadCurrentUser(): AuthResult<GatewayAuthUser> {
        val currentUser = firebaseAuth.currentUser
            ?: return AuthResult.Failure(AuthError.MISSING_CURRENT_USER)
        return runFirebaseCall {
            currentUser.reload().await()
            firebaseAuth.currentUser?.toGatewayUser()
                ?: throw MissingFirebaseUserException
        }
    }

    override suspend fun sendVerificationEmail(): AuthResult<Unit> {
        val currentUser = firebaseAuth.currentUser
            ?: return AuthResult.Failure(AuthError.MISSING_CURRENT_USER)
        return try {
            firebaseAuth.useAppLanguage()
            currentUser.sendEmailVerification().await()
            AuthResult.Success(Unit)
        } catch (exception: CancellationException) {
            throw exception
        } catch (exception: Exception) {
            AuthResult.Failure(
                FirebaseAuthErrorMapper.map(
                    exception = exception,
                    fallback = AuthError.VERIFICATION_EMAIL_FAILED,
                ),
            )
        }
    }

    override fun signOut(): AuthResult<Unit> = try {
        firebaseAuth.signOut()
        AuthResult.Success(Unit)
    } catch (_: Exception) {
        AuthResult.Failure(AuthError.UNKNOWN)
    }

    private suspend fun runFirebaseCall(
        block: suspend () -> GatewayAuthUser,
    ): AuthResult<GatewayAuthUser> = try {
        AuthResult.Success(block())
    } catch (exception: CancellationException) {
        throw exception
    } catch (exception: Exception) {
        AuthResult.Failure(FirebaseAuthErrorMapper.map(exception))
    }
}

internal object FirebaseAuthErrorMapper {
    fun map(
        exception: Throwable,
        fallback: AuthError = AuthError.UNKNOWN,
    ): AuthError {
        if (exception === MissingFirebaseUserException) {
            return AuthError.MISSING_CURRENT_USER
        }
        if (exception is FirebaseNetworkException) {
            return AuthError.NETWORK_UNAVAILABLE
        }
        if (exception is FirebaseTooManyRequestsException) {
            return AuthError.TOO_MANY_REQUESTS
        }
        val errorCode = (exception as? FirebaseAuthException)?.errorCode
        return mapCode(errorCode, fallback)
    }

    internal fun mapCode(
        errorCode: String?,
        fallback: AuthError = AuthError.UNKNOWN,
    ): AuthError = when (errorCode) {
        "ERROR_INVALID_EMAIL" -> AuthError.INVALID_EMAIL
        "ERROR_WEAK_PASSWORD" -> AuthError.WEAK_PASSWORD
        "ERROR_EMAIL_ALREADY_IN_USE",
        "ERROR_ACCOUNT_EXISTS_WITH_DIFFERENT_CREDENTIAL",
        -> AuthError.EMAIL_ALREADY_IN_USE
        "ERROR_USER_DISABLED" -> AuthError.DISABLED_ACCOUNT
        "ERROR_INVALID_CREDENTIAL",
        "ERROR_WRONG_PASSWORD",
        "ERROR_USER_NOT_FOUND",
        "ERROR_EMAIL_CHANGE_NEEDS_VERIFICATION",
        -> AuthError.INVALID_CREDENTIALS
        "ERROR_TOO_MANY_REQUESTS" -> AuthError.TOO_MANY_REQUESTS
        "ERROR_NETWORK_REQUEST_FAILED" -> AuthError.NETWORK_UNAVAILABLE
        else -> fallback
    }
}

private fun FirebaseSignInResult.requireUser(): GatewayAuthUser =
    user?.toGatewayUser() ?: throw MissingFirebaseUserException

private fun FirebaseUser.toGatewayUser(): GatewayAuthUser = GatewayAuthUser(
    uid = uid,
    email = email.orEmpty(),
    isEmailVerified = isEmailVerified,
)

private suspend fun <T> Task<T>.await(): T = suspendCancellableCoroutine { continuation ->
    addOnCompleteListener { completedTask ->
        if (!continuation.isActive) return@addOnCompleteListener
        when {
            completedTask.isSuccessful -> continuation.resume(completedTask.result)
            completedTask.isCanceled -> continuation.cancel()
            else -> continuation.resumeWithException(
                completedTask.exception ?: IllegalStateException("Firebase task failed"),
            )
        }
    }
}

private data object MissingFirebaseUserException : IllegalStateException()
