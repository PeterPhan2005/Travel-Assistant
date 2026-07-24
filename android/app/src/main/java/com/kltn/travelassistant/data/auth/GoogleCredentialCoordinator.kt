package com.kltn.travelassistant.data.auth

import android.app.Activity
import android.content.Context
import android.content.res.Resources
import android.os.Bundle
import androidx.credentials.ClearCredentialStateRequest
import androidx.credentials.Credential
import androidx.credentials.CredentialManager
import androidx.credentials.CustomCredential
import androidx.credentials.GetCredentialRequest
import androidx.credentials.exceptions.GetCredentialCancellationException
import androidx.credentials.exceptions.GetCredentialProviderConfigurationException
import androidx.credentials.exceptions.GetCredentialUnsupportedException
import androidx.credentials.exceptions.NoCredentialException
import com.google.android.libraries.identity.googleid.GetSignInWithGoogleOption
import com.google.android.libraries.identity.googleid.GoogleIdTokenCredential
import com.kltn.travelassistant.R
import com.kltn.travelassistant.feature.auth.domain.AuthError
import com.kltn.travelassistant.feature.auth.domain.AuthRepository
import com.kltn.travelassistant.feature.auth.domain.AuthResult
import com.kltn.travelassistant.feature.auth.domain.CredentialStateClearResult
import com.kltn.travelassistant.feature.auth.domain.GoogleSignInFailure
import com.kltn.travelassistant.feature.auth.domain.GoogleSignInResult
import dagger.hilt.android.qualifiers.ApplicationContext
import javax.inject.Inject
import javax.inject.Singleton
import kotlinx.coroutines.CancellationException

interface GoogleCredentialCoordinator : CredentialStateClearer {
    suspend fun signIn(activity: Activity): GoogleSignInResult
}

fun interface CredentialStateClearer {
    suspend fun clearCredentialState(): CredentialStateClearResult
}

@Singleton
internal class DefaultGoogleCredentialCoordinator @Inject constructor(
    private val credentialAcquirer: GoogleCredentialAcquirer,
    private val authRepository: AuthRepository,
) : GoogleCredentialCoordinator, CredentialStateClearer {
    override suspend fun signIn(activity: Activity): GoogleSignInResult =
        handleAcquisition(credentialAcquirer.acquire(activity))

    override suspend fun clearCredentialState(): CredentialStateClearResult =
        credentialAcquirer.clearCredentialState()

    internal suspend fun handleAcquisition(
        acquisition: GoogleCredentialAcquisition,
    ): GoogleSignInResult = when (acquisition) {
        is GoogleCredentialAcquisition.CredentialReceived -> {
            when (
                val result = authRepository.signInWithGoogleIdToken(
                    acquisition.consumeIdToken(),
                )
            ) {
                is AuthResult.Success -> GoogleSignInResult.Success(result.value)
                is AuthResult.Failure -> GoogleSignInResult.Failure(
                    result.error.toGoogleSignInFailure(),
                )
            }
        }
        GoogleCredentialAcquisition.Cancelled -> GoogleSignInResult.Cancelled
        GoogleCredentialAcquisition.NoCredential -> GoogleSignInResult.Failure(
            GoogleSignInFailure.NO_CREDENTIAL,
        )
        GoogleCredentialAcquisition.ConfigurationError -> GoogleSignInResult.Failure(
            GoogleSignInFailure.CONFIGURATION,
        )
        GoogleCredentialAcquisition.InvalidCredential -> GoogleSignInResult.Failure(
            GoogleSignInFailure.INVALID_CREDENTIAL,
        )
        GoogleCredentialAcquisition.ProviderUnavailable -> GoogleSignInResult.Failure(
            GoogleSignInFailure.PROVIDER_UNAVAILABLE,
        )
        GoogleCredentialAcquisition.Failure -> GoogleSignInResult.Failure(
            GoogleSignInFailure.UNKNOWN,
        )
    }
}

internal interface GoogleCredentialAcquirer {
    suspend fun acquire(activity: Activity): GoogleCredentialAcquisition

    suspend fun clearCredentialState(): CredentialStateClearResult
}

@Singleton
internal class AndroidGoogleCredentialAcquirer @Inject constructor(
    @ApplicationContext context: Context,
    private val acquisitionEngine: GoogleCredentialAcquisitionEngine,
) : GoogleCredentialAcquirer {
    private val credentialManager = CredentialManager.create(context)

    override suspend fun acquire(activity: Activity): GoogleCredentialAcquisition =
        acquisitionEngine.acquireWith { serverClientId ->
            val option = GetSignInWithGoogleOption.Builder(serverClientId).build()
            val request = GetCredentialRequest.Builder()
                .addCredentialOption(option)
                .build()
            credentialManager.getCredential(
                context = activity,
                request = request,
            ).credential.toEnvelope()
        }

    override suspend fun clearCredentialState(): CredentialStateClearResult = try {
        credentialManager.clearCredentialState(ClearCredentialStateRequest())
        CredentialStateClearResult.Success
    } catch (exception: CancellationException) {
        throw exception
    } catch (_: Exception) {
        CredentialStateClearResult.Failure
    }
}

internal class GoogleCredentialAcquisitionEngine @Inject constructor(
    private val clientIdProvider: GoogleClientIdProvider,
    private val tokenParser: GoogleIdTokenParser,
) {
    internal suspend fun acquireWith(
        requestCredential: suspend (serverClientId: String) -> CredentialEnvelope,
    ): GoogleCredentialAcquisition {
        val serverClientId = clientIdProvider.getServerClientId()
            ?.trim()
            ?.takeIf(String::isNotEmpty)
            ?: return GoogleCredentialAcquisition.ConfigurationError
        return try {
            when (val envelope = requestCredential(serverClientId)) {
                is CredentialEnvelope.Custom -> parseCustomCredential(envelope)
                CredentialEnvelope.Unsupported -> GoogleCredentialAcquisition.InvalidCredential
            }
        } catch (exception: CancellationException) {
            throw exception
        } catch (_: GetCredentialCancellationException) {
            GoogleCredentialAcquisition.Cancelled
        } catch (_: NoCredentialException) {
            GoogleCredentialAcquisition.NoCredential
        } catch (_: GetCredentialProviderConfigurationException) {
            GoogleCredentialAcquisition.ProviderUnavailable
        } catch (_: GetCredentialUnsupportedException) {
            GoogleCredentialAcquisition.ProviderUnavailable
        } catch (_: Exception) {
            GoogleCredentialAcquisition.Failure
        }
    }

    private fun parseCustomCredential(
        credential: CredentialEnvelope.Custom,
    ): GoogleCredentialAcquisition {
        if (credential.type != GoogleIdTokenCredential.TYPE_GOOGLE_ID_TOKEN_CREDENTIAL) {
            return GoogleCredentialAcquisition.InvalidCredential
        }
        return try {
            val idToken = tokenParser.parse(credential)
            if (idToken.isBlank()) {
                GoogleCredentialAcquisition.InvalidCredential
            } else {
                GoogleCredentialAcquisition.CredentialReceived(idToken)
            }
        } catch (_: Exception) {
            GoogleCredentialAcquisition.InvalidCredential
        }
    }
}

internal interface GoogleClientIdProvider {
    fun getServerClientId(): String?
}

internal class GeneratedGoogleClientIdProvider @Inject constructor(
    @param:ApplicationContext private val context: Context,
) : GoogleClientIdProvider {
    override fun getServerClientId(): String? = try {
        context.getString(R.string.default_web_client_id)
    } catch (_: Resources.NotFoundException) {
        null
    }
}

internal interface GoogleIdTokenParser {
    fun parse(credential: CredentialEnvelope.Custom): String
}

internal class DefaultGoogleIdTokenParser @Inject constructor() : GoogleIdTokenParser {
    override fun parse(credential: CredentialEnvelope.Custom): String {
        val data = credential.payload as? Bundle
            ?: throw IllegalArgumentException("Unsupported credential payload")
        return GoogleIdTokenCredential.createFrom(data).idToken
    }
}

internal sealed interface GoogleCredentialAcquisition {
    class CredentialReceived(private val idToken: String) : GoogleCredentialAcquisition {
        init {
            require(idToken.isNotBlank())
        }

        internal fun consumeIdToken(): String = idToken

        override fun toString(): String = "CredentialReceived"
    }

    data object Cancelled : GoogleCredentialAcquisition

    data object NoCredential : GoogleCredentialAcquisition

    data object ConfigurationError : GoogleCredentialAcquisition

    data object InvalidCredential : GoogleCredentialAcquisition

    data object ProviderUnavailable : GoogleCredentialAcquisition

    data object Failure : GoogleCredentialAcquisition
}

internal sealed interface CredentialEnvelope {
    class Custom(
        val type: String,
        val payload: Any,
    ) : CredentialEnvelope {
        override fun toString(): String = "CustomCredential"
    }

    data object Unsupported : CredentialEnvelope
}

private fun Credential.toEnvelope(): CredentialEnvelope = when (this) {
    is CustomCredential -> CredentialEnvelope.Custom(type = type, payload = data)
    else -> CredentialEnvelope.Unsupported
}

private fun AuthError.toGoogleSignInFailure(): GoogleSignInFailure = when (this) {
    AuthError.INVALID_CREDENTIALS -> GoogleSignInFailure.INVALID_CREDENTIAL
    AuthError.ACCOUNT_PROVIDER_CONFLICT,
    AuthError.EMAIL_ALREADY_IN_USE,
    -> GoogleSignInFailure.ACCOUNT_PROVIDER_CONFLICT
    AuthError.DISABLED_ACCOUNT -> GoogleSignInFailure.DISABLED_ACCOUNT
    AuthError.TOO_MANY_REQUESTS -> GoogleSignInFailure.TOO_MANY_REQUESTS
    AuthError.NETWORK_UNAVAILABLE -> GoogleSignInFailure.NETWORK_UNAVAILABLE
    AuthError.INVALID_EMAIL,
    AuthError.WEAK_PASSWORD,
    AuthError.VERIFICATION_EMAIL_FAILED,
    AuthError.MISSING_CURRENT_USER,
    AuthError.UNKNOWN,
    -> GoogleSignInFailure.UNKNOWN
}
