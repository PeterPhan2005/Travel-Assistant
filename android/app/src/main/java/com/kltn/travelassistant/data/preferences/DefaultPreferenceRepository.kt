package com.kltn.travelassistant.data.preferences

import com.kltn.travelassistant.feature.auth.domain.AuthRepository
import com.kltn.travelassistant.feature.auth.domain.AuthSession
import com.kltn.travelassistant.feature.preferences.domain.PreferenceDocument
import com.kltn.travelassistant.feature.preferences.domain.PreferenceRepository
import com.kltn.travelassistant.feature.preferences.domain.PreferenceSyncState
import com.kltn.travelassistant.feature.preferences.domain.PreferenceUpdateResult
import javax.inject.Inject
import javax.inject.Singleton
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.catch
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.distinctUntilChanged
import kotlinx.coroutines.flow.flatMapLatest
import kotlinx.coroutines.flow.flowOf
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch

@Singleton
@OptIn(ExperimentalCoroutinesApi::class)
internal class DefaultPreferenceRepository @Inject constructor(
    private val authRepository: AuthRepository,
    private val firebaseSession: FirebasePreferenceSession,
    private val localStore: PreferenceLocalStore,
    private val scheduler: PreferenceWorkScheduler,
) : PreferenceRepository {
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.Default)
    private val session = authRepository.observeSession()
        .stateIn(scope, SharingStarted.Eagerly, AuthSession.Checking)

    override val state = combine(
        session,
        session.flatMapLatest(::localRecordForSession),
        scheduler.observe()
            .catch { emit(PreferenceWorkState.RetryableFailure) },
        ::mapState,
    ).stateIn(
        scope,
        SharingStarted.Eagerly,
        PreferenceSyncState.LoadingLocal,
    )

    init {
        scope.launch {
            session
                .map { auth ->
                    (auth as? AuthSession.Authenticated)
                        ?.user
                        ?.uid
                        ?.let(PreferenceOwnerKey::fromUid)
                }
                .distinctUntilChanged()
                .collect { ownerKey ->
                    if (ownerKey != null) scheduler.enqueue()
                }
        }
    }

    override suspend fun updateLocal(
        document: PreferenceDocument,
    ): PreferenceUpdateResult {
        val account = firebaseSession.currentVerifiedAccount()
            ?: return PreferenceUpdateResult.SignedOut
        return try {
            localStore.saveLocalEdit(account.ownerKey, document)
            scheduler.enqueue()
            PreferenceUpdateResult.SavedAndQueued
        } catch (exception: CancellationException) {
            throw exception
        } catch (exception: InvalidPreferenceDocumentException) {
            PreferenceUpdateResult.InvalidDocument
        } catch (exception: Exception) {
            PreferenceUpdateResult.StorageFailure
        }
    }

    override fun refresh() {
        if (firebaseSession.currentVerifiedAccount() != null) {
            scheduler.enqueue()
        }
    }

    override fun retry() = refresh()

    private fun localRecordForSession(
        authSession: AuthSession,
    ): Flow<LocalRecordState> = when (authSession) {
        is AuthSession.Authenticated -> localStore.observe(
            PreferenceOwnerKey.fromUid(authSession.user.uid),
        ).map<LocalPreferenceRecord?, LocalRecordState> { record ->
            LocalRecordState.Loaded(record)
        }.catch {
            emit(LocalRecordState.Invalid)
        }
        AuthSession.Checking -> flowOf(LocalRecordState.Loading)
        AuthSession.Error -> flowOf(LocalRecordState.Invalid)
        AuthSession.SignedOut,
        is AuthSession.VerificationRequired,
        -> flowOf(LocalRecordState.Loaded(null))
    }

    private fun mapState(
        authSession: AuthSession,
        localState: LocalRecordState,
        workState: PreferenceWorkState,
    ): PreferenceSyncState {
        if (
            authSession == AuthSession.SignedOut ||
            authSession is AuthSession.VerificationRequired
        ) {
            return PreferenceSyncState.SignedOut
        }
        if (authSession == AuthSession.Error) {
            return PreferenceSyncState.AuthenticationFailure
        }
        if (authSession == AuthSession.Checking || localState == LocalRecordState.Loading) {
            return PreferenceSyncState.LoadingLocal
        }
        if (
            localState == LocalRecordState.Invalid ||
            workState == PreferenceWorkState.InvalidDocument
        ) {
            return PreferenceSyncState.InvalidDocument
        }
        if (workState == PreferenceWorkState.AuthenticationFailure) {
            return PreferenceSyncState.AuthenticationFailure
        }

        val record = (localState as LocalRecordState.Loaded).record
        val document = record?.document ?: PreferenceDocument()
        return when (workState) {
            PreferenceWorkState.Running ->
                PreferenceSyncState.Synchronizing(document)
            PreferenceWorkState.RetryableFailure ->
                PreferenceSyncState.RetryableFailure(document)
            PreferenceWorkState.Succeeded -> record?.lastServerUpdatedAt?.let {
                PreferenceSyncState.Synchronized(document, it)
            } ?: PreferenceSyncState.LocalCurrent(document)
            PreferenceWorkState.Idle -> if (record?.pendingSync == true) {
                PreferenceSyncState.PendingOffline(document)
            } else {
                record?.lastServerUpdatedAt?.let {
                    PreferenceSyncState.Synchronized(document, it)
                } ?: PreferenceSyncState.LocalCurrent(document)
            }
            PreferenceWorkState.AuthenticationFailure ->
                PreferenceSyncState.AuthenticationFailure
            PreferenceWorkState.InvalidDocument ->
                PreferenceSyncState.InvalidDocument
        }
    }

    private sealed interface LocalRecordState {
        data object Loading : LocalRecordState

        data object Invalid : LocalRecordState

        data class Loaded(val record: LocalPreferenceRecord?) : LocalRecordState
    }
}
