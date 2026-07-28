package com.kltn.travelassistant.data.preferences

import com.google.android.gms.tasks.Task
import com.google.firebase.FirebaseNetworkException
import com.google.firebase.auth.FirebaseAuth
import com.google.firebase.auth.GetTokenResult
import javax.inject.Inject
import javax.inject.Singleton
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.suspendCancellableCoroutine
import kotlin.coroutines.resume
import kotlin.coroutines.resumeWithException

internal data class ActivePreferenceAccount(val ownerKey: String)

internal sealed interface PreferenceTokenResult {
    data class Success(val token: String) : PreferenceTokenResult

    data object AuthenticationFailure : PreferenceTokenResult

    data object RetryableFailure : PreferenceTokenResult
}

internal interface FirebasePreferenceSession {
    fun currentVerifiedAccount(): ActivePreferenceAccount?

    suspend fun idToken(
        expectedOwnerKey: String,
        forceRefresh: Boolean,
    ): PreferenceTokenResult
}

@Singleton
internal class DefaultFirebasePreferenceSession @Inject constructor(
    private val firebaseAuth: FirebaseAuth,
) : FirebasePreferenceSession {
    override fun currentVerifiedAccount(): ActivePreferenceAccount? {
        val user = firebaseAuth.currentUser ?: return null
        if (!user.isEmailVerified || user.uid.isBlank()) return null
        return ActivePreferenceAccount(PreferenceOwnerKey.fromUid(user.uid))
    }

    override suspend fun idToken(
        expectedOwnerKey: String,
        forceRefresh: Boolean,
    ): PreferenceTokenResult {
        val user = firebaseAuth.currentUser
            ?: return PreferenceTokenResult.AuthenticationFailure
        if (
            !user.isEmailVerified ||
            PreferenceOwnerKey.fromUid(user.uid) != expectedOwnerKey
        ) {
            return PreferenceTokenResult.AuthenticationFailure
        }
        return try {
            val token = user.getIdToken(forceRefresh).await().token
            if (token.isNullOrBlank() || token.any(Char::isWhitespace)) {
                PreferenceTokenResult.AuthenticationFailure
            } else {
                PreferenceTokenResult.Success(token)
            }
        } catch (exception: CancellationException) {
            throw exception
        } catch (exception: FirebaseNetworkException) {
            PreferenceTokenResult.RetryableFailure
        } catch (exception: Exception) {
            PreferenceTokenResult.AuthenticationFailure
        }
    }
}

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

