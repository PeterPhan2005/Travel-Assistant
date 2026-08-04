package com.kltn.travelassistant.feature.itinerary.data

import com.kltn.travelassistant.data.local.dao.ItineraryDao
import com.kltn.travelassistant.data.local.entity.LocalItineraryEntity
import com.kltn.travelassistant.data.local.entity.LocalItineraryItemEntity
import com.kltn.travelassistant.data.local.model.LocalItineraryWithItems
import com.kltn.travelassistant.data.preferences.FirebasePreferenceSession
import com.kltn.travelassistant.data.preferences.PreferenceOwnerKey
import com.kltn.travelassistant.feature.auth.domain.AuthRepository
import com.kltn.travelassistant.feature.auth.domain.AuthSession
import com.kltn.travelassistant.feature.itinerary.domain.ItineraryCity
import com.kltn.travelassistant.feature.itinerary.domain.ItineraryDraft
import com.kltn.travelassistant.feature.itinerary.domain.ItineraryDraftItem
import com.kltn.travelassistant.feature.itinerary.domain.ItineraryDraftRequest
import com.kltn.travelassistant.feature.itinerary.domain.ItineraryDraftWarning
import com.kltn.travelassistant.feature.itinerary.domain.ItinerarySaveBoundary
import com.kltn.travelassistant.feature.itinerary.domain.ItinerarySaveResult
import com.kltn.travelassistant.feature.itinerary.domain.ItinerarySyncState
import com.kltn.travelassistant.feature.itinerary.domain.SavedItinerary
import com.kltn.travelassistant.feature.itinerary.domain.SavedItineraryDeleteResult
import com.kltn.travelassistant.feature.itinerary.domain.SavedItineraryLibraryState
import com.kltn.travelassistant.feature.itinerary.domain.SavedItineraryRepository
import com.kltn.travelassistant.feature.itinerary.domain.isValidDraftForRequest
import java.time.DateTimeException
import java.time.Instant
import java.time.LocalDate
import java.time.LocalTime
import java.time.ZoneId
import java.time.ZonedDateTime
import java.util.UUID
import javax.inject.Inject
import javax.inject.Singleton
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.catch
import kotlinx.coroutines.flow.flatMapLatest
import kotlinx.coroutines.flow.flowOf
import kotlinx.coroutines.flow.map

internal const val ITINERARY_SYNC_PENDING = "pending"
internal const val ITINERARY_SYNC_SYNCED = "synced"
internal const val ITINERARY_SYNC_CONFLICT = "conflict"
internal const val ITINERARY_SYNC_FAILED = "failed"

@Singleton
@OptIn(ExperimentalCoroutinesApi::class)
internal class RoomSavedItineraryRepository @Inject constructor(
    private val itineraryDao: ItineraryDao,
    private val authRepository: AuthRepository,
    private val firebaseSession: FirebasePreferenceSession,
    private val scheduler: ItineraryWorkScheduler,
    private val codec: SavedItineraryLocalCodec,
) : ItinerarySaveBoundary, SavedItineraryRepository {
    override fun observeLibrary(): Flow<SavedItineraryLibraryState> =
        authRepository.observeSession().flatMapLatest { session ->
            when (session) {
                is AuthSession.Authenticated -> {
                    val accountKey = PreferenceOwnerKey.fromUid(session.user.uid)
                    itineraryDao.observeReadableItineraries(accountKey)
                        .map<List<LocalItineraryWithItems>, SavedItineraryLibraryState> {
                            rows ->
                            SavedItineraryLibraryState.Content(
                                rows.map { it.toDomain(accountKey, codec) },
                            )
                        }
                        .catch { emit(SavedItineraryLibraryState.Failed) }
                }
                AuthSession.Checking -> flowOf(SavedItineraryLibraryState.Loading)
                AuthSession.SignedOut,
                is AuthSession.VerificationRequired,
                -> flowOf(SavedItineraryLibraryState.SignedOut)
                AuthSession.Error -> flowOf(SavedItineraryLibraryState.Failed)
            }
        }

    override suspend fun save(draft: ItineraryDraft): ItinerarySaveResult {
        val account = firebaseSession.currentVerifiedAccount()
            ?: return ItinerarySaveResult.AuthenticationRequired
        if (!draft.isValidForPersistence()) return ItinerarySaveResult.Failed
        val itineraryId = UUID.randomUUID().toString()
        val localRevision = 1L
        try {
            val now = System.currentTimeMillis()
            val entity = draft.toEntity(
                itineraryId = itineraryId,
                accountKey = account.ownerKey,
                now = now,
                codec = codec,
            )
            itineraryDao.replaceSnapshot(
                itinerary = entity,
                items = draft.toItemEntities(itineraryId),
            )
        } catch (exception: CancellationException) {
            throw exception
        } catch (exception: Exception) {
            return ItinerarySaveResult.Failed
        }
        enqueueOrMarkFailed(
            accountKey = account.ownerKey,
            itineraryId = itineraryId,
            localRevision = localRevision,
        )
        return ItinerarySaveResult.SavedLocally
    }

    override suspend fun delete(
        itineraryId: String,
    ): SavedItineraryDeleteResult {
        val account = firebaseSession.currentVerifiedAccount()
            ?: return SavedItineraryDeleteResult.AuthenticationRequired
        if (!itineraryId.isUuid()) return SavedItineraryDeleteResult.NotFound
        val localRevision: Long
        try {
            val changed = itineraryDao.markDeletedAndRemoveItems(
                accountKey = account.ownerKey,
                itineraryId = itineraryId,
                updatedAtEpochMillis = System.currentTimeMillis(),
            )
            if (!changed) {
                return SavedItineraryDeleteResult.NotFound
            }
            localRevision = itineraryDao.getItineraryById(account.ownerKey, itineraryId)
                ?.localRevision
                ?: return SavedItineraryDeleteResult.Failed
        } catch (exception: CancellationException) {
            throw exception
        } catch (exception: Exception) {
            return SavedItineraryDeleteResult.Failed
        }
        enqueueOrMarkFailed(account.ownerKey, itineraryId, localRevision)
        return SavedItineraryDeleteResult.DeletedLocally
    }

    private suspend fun enqueueOrMarkFailed(
        accountKey: String,
        itineraryId: String,
        localRevision: Long,
    ) {
        try {
            scheduler.enqueue(itineraryId)
        } catch (exception: CancellationException) {
            throw exception
        } catch (_: Exception) {
            try {
                itineraryDao.markSyncState(
                    accountKey = accountKey,
                    itineraryId = itineraryId,
                    expectedLocalRevision = localRevision,
                    syncState = ITINERARY_SYNC_FAILED,
                )
            } catch (exception: CancellationException) {
                throw exception
            } catch (_: Exception) {
                Unit
            }
        }
    }
}

private fun ItineraryDraft.isValidForPersistence(): Boolean =
    isValidDraftForRequest(
        draft = this,
        request = ItineraryDraftRequest(
            city = city,
            localDate = localDate,
            timezone = timezone,
            startLocalTime = startLocalTime,
            endLocalTime = endLocalTime,
            maximumStops = 20,
            notes = null,
            currentLocation = null,
        ),
    )

private fun ItineraryDraft.toEntity(
    itineraryId: String,
    accountKey: String,
    now: Long,
    codec: SavedItineraryLocalCodec,
): LocalItineraryEntity = LocalItineraryEntity(
    itineraryId = itineraryId,
    title = when (city) {
        ItineraryCity.HO_CHI_MINH_CITY -> "Lịch trình TP. Hồ Chí Minh · $localDate"
        ItineraryCity.BANGKOK -> "Lịch trình Bangkok · $localDate"
    },
    accountKey = accountKey,
    city = city.toWire(),
    localDate = localDate.toString(),
    timezone = timezone,
    startLocalTime = startLocalTime.toString(),
    endLocalTime = endLocalTime.toString(),
    assumptionsJson = codec.encodeTextList(assumptions),
    warningsJson = codec.encodeTextList(warnings.map(ItineraryDraftWarning::message)),
    localRevision = 1,
    serverRevision = 0,
    syncState = ITINERARY_SYNC_PENDING,
    isDeleted = false,
    createdAtEpochMillis = now,
    updatedAtEpochMillis = now,
)

private fun ItineraryDraft.toItemEntities(
    itineraryId: String,
): List<LocalItineraryItemEntity> {
    val zone = ZoneId.of(timezone)
    return items.mapIndexed { position, item ->
        LocalItineraryItemEntity(
            itineraryItemId = UUID.nameUUIDFromBytes(
                "$itineraryId:$position".toByteArray(Charsets.UTF_8),
            ).toString(),
            itineraryId = itineraryId,
            poiId = null,
            title = item.title,
            position = position,
            startAtEpochMillis = ZonedDateTime.of(
                localDate,
                item.startLocalTime,
                zone,
            ).toInstant().toEpochMilli(),
            endAtEpochMillis = ZonedDateTime.of(
                localDate,
                item.endLocalTime,
                zone,
            ).toInstant().toEpochMilli(),
            travelTimeMinutes = null,
            notes = null,
        )
    }
}

internal fun LocalItineraryWithItems.toDomain(
    expectedAccountKey: String,
    codec: SavedItineraryLocalCodec,
): SavedItinerary {
    val row = itinerary
    if (
        row.accountKey != expectedAccountKey ||
        row.isDeleted ||
        row.localRevision < 1 ||
        row.serverRevision < 0 ||
        !row.itineraryId.isUuid()
    ) {
        throw InvalidSavedItineraryException()
    }
    val city = row.city.toCity()
    val localDate = parseDate(row.localDate)
    val start = parseTime(row.startLocalTime)
    val end = parseTime(row.endLocalTime)
    if (row.timezone != city.timezone) throw InvalidSavedItineraryException()
    val zone = try {
        ZoneId.of(row.timezone)
    } catch (exception: DateTimeException) {
        throw InvalidSavedItineraryException()
    }
    val orderedItems = items.sortedWith(
        compareBy(LocalItineraryItemEntity::position)
            .thenBy(LocalItineraryItemEntity::itineraryItemId),
    )
    val draft = ItineraryDraft(
        city = city,
        localDate = localDate,
        timezone = row.timezone,
        startLocalTime = start,
        endLocalTime = end,
        items = orderedItems.mapIndexed { expectedPosition, item ->
            if (
                item.itineraryId != row.itineraryId ||
                item.position != expectedPosition ||
                item.notes != null ||
                item.poiId != null ||
                item.startAtEpochMillis == null ||
                item.endAtEpochMillis == null
            ) {
                throw InvalidSavedItineraryException()
            }
            ItineraryDraftItem(
                title = item.title,
                startLocalTime = Instant.ofEpochMilli(item.startAtEpochMillis)
                    .atZone(zone).toLocalTime(),
                endLocalTime = Instant.ofEpochMilli(item.endAtEpochMillis)
                    .atZone(zone).toLocalTime(),
            )
        },
        assumptions = codec.decodeTextList(row.assumptionsJson),
        warnings = codec.decodeTextList(row.warningsJson).map(::ItineraryDraftWarning),
    )
    if (!draft.isValidForPersistence()) throw InvalidSavedItineraryException()
    return SavedItinerary(
        id = row.itineraryId,
        title = row.title,
        draft = draft,
        syncState = row.syncState.toSyncState(),
    )
}

private fun String.toCity(): ItineraryCity = when (this) {
    "hcmc" -> ItineraryCity.HO_CHI_MINH_CITY
    "bkk" -> ItineraryCity.BANGKOK
    else -> throw InvalidSavedItineraryException()
}

internal fun ItineraryCity.toWire(): String = when (this) {
    ItineraryCity.HO_CHI_MINH_CITY -> "hcmc"
    ItineraryCity.BANGKOK -> "bkk"
}

private fun String.toSyncState(): ItinerarySyncState = when (this) {
    ITINERARY_SYNC_PENDING -> ItinerarySyncState.PENDING
    ITINERARY_SYNC_SYNCED -> ItinerarySyncState.SYNCED
    ITINERARY_SYNC_CONFLICT -> ItinerarySyncState.CONFLICT
    ITINERARY_SYNC_FAILED -> ItinerarySyncState.FAILED
    else -> throw InvalidSavedItineraryException()
}

private fun parseDate(value: String): LocalDate = try {
    LocalDate.parse(value)
} catch (exception: DateTimeException) {
    throw InvalidSavedItineraryException()
}

private fun parseTime(value: String): LocalTime = try {
    LocalTime.parse(value)
} catch (exception: DateTimeException) {
    throw InvalidSavedItineraryException()
}

private fun String.isUuid(): Boolean = try {
    UUID.fromString(this).toString() == lowercase()
} catch (exception: IllegalArgumentException) {
    false
}
