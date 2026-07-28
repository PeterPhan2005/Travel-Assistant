package com.kltn.travelassistant.data.preferences

import javax.inject.Inject
import javax.inject.Singleton
import kotlinx.coroutines.CancellationException

internal enum class PreferenceSyncOutcome {
    SUCCESS,
    NEWER_LOCAL_REVISION,
    RETRYABLE_FAILURE,
    AUTHENTICATION_FAILURE,
    INVALID_DOCUMENT,
}

@Singleton
internal class PreferenceSyncEngine @Inject constructor(
    private val session: FirebasePreferenceSession,
    private val localStore: PreferenceLocalStore,
    private val api: PreferenceApi,
) {
    suspend fun synchronizeCurrentAccount(): PreferenceSyncOutcome {
        val account = session.currentVerifiedAccount()
            ?: return PreferenceSyncOutcome.AUTHENTICATION_FAILURE
        return try {
            val local = localStore.read(account.ownerKey)
            if (local?.pendingSync == true) {
                push(account, local)
            } else {
                refresh(account)
            }
        } catch (exception: CancellationException) {
            throw exception
        } catch (exception: InvalidPreferenceDocumentException) {
            PreferenceSyncOutcome.INVALID_DOCUMENT
        } catch (exception: PreferenceApiException) {
            exception.error.toSyncOutcome()
        } catch (exception: Exception) {
            PreferenceSyncOutcome.RETRYABLE_FAILURE
        }
    }

    private suspend fun push(
        account: ActivePreferenceAccount,
        snapshot: LocalPreferenceRecord,
    ): PreferenceSyncOutcome {
        val server = api.put(account.ownerKey, snapshot.document)
        if (server.updatedAt == null) {
            return PreferenceSyncOutcome.INVALID_DOCUMENT
        }
        val completed = localStore.completePush(
            ownerKey = account.ownerKey,
            expectedRevision = snapshot.localRevision,
            server = server,
        )
        return if (!completed) {
            PreferenceSyncOutcome.NEWER_LOCAL_REVISION
        } else {
            accountCompletionOutcome(account)
        }
    }

    private suspend fun refresh(
        account: ActivePreferenceAccount,
    ): PreferenceSyncOutcome {
        val server = api.get(account.ownerKey)
        val applied = localStore.applyServerRefresh(account.ownerKey, server)
        return if (!applied) {
            PreferenceSyncOutcome.NEWER_LOCAL_REVISION
        } else {
            accountCompletionOutcome(account)
        }
    }

    private fun accountCompletionOutcome(
        synchronizedAccount: ActivePreferenceAccount,
    ): PreferenceSyncOutcome {
        val activeAccount = session.currentVerifiedAccount()
            ?: return PreferenceSyncOutcome.AUTHENTICATION_FAILURE
        return if (activeAccount.ownerKey == synchronizedAccount.ownerKey) {
            PreferenceSyncOutcome.SUCCESS
        } else {
            PreferenceSyncOutcome.NEWER_LOCAL_REVISION
        }
    }
}

private fun PreferenceApiError.toSyncOutcome(): PreferenceSyncOutcome = when (this) {
    PreferenceApiError.RETRYABLE -> PreferenceSyncOutcome.RETRYABLE_FAILURE
    PreferenceApiError.AUTHENTICATION -> PreferenceSyncOutcome.AUTHENTICATION_FAILURE
    PreferenceApiError.INVALID_DOCUMENT,
    PreferenceApiError.INVALID_RESPONSE,
    PreferenceApiError.CONFIGURATION,
    -> PreferenceSyncOutcome.INVALID_DOCUMENT
}
