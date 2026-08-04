package com.kltn.travelassistant.feature.itinerary.data

import com.kltn.travelassistant.data.local.dao.ItineraryDao
import com.kltn.travelassistant.data.local.model.LocalItineraryWithItems
import com.kltn.travelassistant.data.preferences.FirebasePreferenceSession
import java.util.UUID
import javax.inject.Inject
import javax.inject.Singleton
import kotlinx.coroutines.CancellationException

internal enum class ItinerarySyncOutcome {
    SUCCESS,
    NEWER_LOCAL_REVISION,
    RETRYABLE_FAILURE,
    CONFLICT,
    AUTHENTICATION_FAILURE,
    INVALID_DATA,
}

@Singleton
internal class SavedItinerarySyncEngine @Inject constructor(
    private val session: FirebasePreferenceSession,
    private val itineraryDao: ItineraryDao,
    private val api: SavedItineraryApi,
    private val codec: SavedItineraryLocalCodec,
) {
    suspend fun synchronize(itineraryId: String): ItinerarySyncOutcome {
        if (!itineraryId.isCanonicalUuid()) return ItinerarySyncOutcome.INVALID_DATA
        val account = session.currentVerifiedAccount()
        if (account == null) {
            itineraryDao.markPendingSyncStateByItineraryId(
                itineraryId,
                ITINERARY_SYNC_FAILED,
            )
            return ItinerarySyncOutcome.AUTHENTICATION_FAILURE
        }
        return try {
            val row = itineraryDao.getItineraryWithItems(account.ownerKey, itineraryId)
                ?: return ItinerarySyncOutcome.SUCCESS
            if (row.itinerary.syncState != ITINERARY_SYNC_PENDING) {
                return ItinerarySyncOutcome.SUCCESS
            }
            val snapshot = row.toSyncSnapshot(account.ownerKey, codec)
            when (val remote = api.synchronize(account.ownerKey, snapshot)) {
                is ItineraryRemoteResult.Success -> complete(snapshot, account.ownerKey, remote)
                ItineraryRemoteResult.Conflict -> {
                    val marked = itineraryDao.markSyncState(
                        accountKey = account.ownerKey,
                        itineraryId = itineraryId,
                        expectedLocalRevision = snapshot.localRevision,
                        syncState = ITINERARY_SYNC_CONFLICT,
                    ) == 1
                    if (marked) {
                        ItinerarySyncOutcome.CONFLICT
                    } else {
                        ItinerarySyncOutcome.NEWER_LOCAL_REVISION
                    }
                }
                ItineraryRemoteResult.RetryableFailure ->
                    ItinerarySyncOutcome.RETRYABLE_FAILURE
                ItineraryRemoteResult.AuthenticationFailure -> {
                    markFailed(itineraryId)
                    ItinerarySyncOutcome.AUTHENTICATION_FAILURE
                }
                ItineraryRemoteResult.InvalidData -> {
                    markFailed(itineraryId)
                    ItinerarySyncOutcome.INVALID_DATA
                }
            }
        } catch (exception: CancellationException) {
            throw exception
        } catch (exception: InvalidSavedItineraryException) {
            markFailed(itineraryId)
            ItinerarySyncOutcome.INVALID_DATA
        } catch (exception: Exception) {
            ItinerarySyncOutcome.RETRYABLE_FAILURE
        }
    }

    suspend fun markRetryExhausted(itineraryId: String) {
        markFailed(itineraryId)
    }

    private suspend fun complete(
        snapshot: SavedItinerarySyncSnapshot,
        accountKey: String,
        remote: ItineraryRemoteResult.Success,
    ): ItinerarySyncOutcome {
        val completed = itineraryDao.completeSync(
            accountKey = accountKey,
            itineraryId = snapshot.id,
            expectedLocalRevision = snapshot.localRevision,
            serverRevision = remote.serverRevision,
        ) == 1
        if (completed) return ItinerarySyncOutcome.SUCCESS
        itineraryDao.recordServerRevisionForNewerLocalState(
            accountKey = accountKey,
            itineraryId = snapshot.id,
            staleLocalRevision = snapshot.localRevision,
            serverRevision = remote.serverRevision,
        )
        return ItinerarySyncOutcome.NEWER_LOCAL_REVISION
    }

    private suspend fun markFailed(itineraryId: String) {
        val account = session.currentVerifiedAccount()
        if (account == null) {
            itineraryDao.markPendingSyncStateByItineraryId(
                itineraryId,
                ITINERARY_SYNC_FAILED,
            )
            return
        }
        val row = itineraryDao.getItineraryById(account.ownerKey, itineraryId) ?: return
        itineraryDao.markSyncState(
            accountKey = account.ownerKey,
            itineraryId = itineraryId,
            expectedLocalRevision = row.localRevision,
            syncState = ITINERARY_SYNC_FAILED,
        )
    }
}

private fun LocalItineraryWithItems.toSyncSnapshot(
    accountKey: String,
    codec: SavedItineraryLocalCodec,
): SavedItinerarySyncSnapshot {
    val row = itinerary
    if (
        row.accountKey != accountKey ||
        row.localRevision < 1 ||
        row.serverRevision < 0 ||
        !row.itineraryId.isCanonicalUuid()
    ) {
        throw InvalidSavedItineraryException()
    }
    if (row.isDeleted) {
        if (items.isNotEmpty()) throw InvalidSavedItineraryException()
        return SavedItinerarySyncSnapshot(
            id = row.itineraryId,
            localRevision = row.localRevision,
            serverRevision = row.serverRevision,
            deleted = true,
            title = "",
            city = "",
            localDate = "",
            timezone = "",
            startLocalTime = "",
            endLocalTime = "",
            items = emptyList(),
            assumptions = emptyList(),
            warnings = emptyList(),
        )
    }
    val domain = toDomain(accountKey, codec)
    val orderedEntities = items.sortedBy { it.position }
    return SavedItinerarySyncSnapshot(
        id = row.itineraryId,
        localRevision = row.localRevision,
        serverRevision = row.serverRevision,
        deleted = false,
        title = row.title,
        city = domain.draft.city.toWire(),
        localDate = domain.draft.localDate.toString(),
        timezone = domain.draft.timezone,
        startLocalTime = domain.draft.startLocalTime.toString(),
        endLocalTime = domain.draft.endLocalTime.toString(),
        items = domain.draft.items.mapIndexed { position, item ->
            val entity = orderedEntities[position]
            if (!entity.itineraryItemId.isCanonicalUuid()) {
                throw InvalidSavedItineraryException()
            }
            SavedItinerarySyncItem(
                id = entity.itineraryItemId,
                position = position,
                title = item.title,
                startLocalTime = item.startLocalTime.toString(),
                endLocalTime = item.endLocalTime.toString(),
            )
        },
        assumptions = domain.draft.assumptions,
        warnings = domain.draft.warnings.map { it.message },
    )
}

private fun String.isCanonicalUuid(): Boolean = try {
    UUID.fromString(this).toString() == lowercase()
} catch (exception: IllegalArgumentException) {
    false
}
