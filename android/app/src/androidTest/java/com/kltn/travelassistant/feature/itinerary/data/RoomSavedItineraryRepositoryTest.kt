package com.kltn.travelassistant.feature.itinerary.data

import android.content.Context
import androidx.room.Room
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.kltn.travelassistant.data.local.TravelAssistantDatabase
import com.kltn.travelassistant.data.preferences.ActivePreferenceAccount
import com.kltn.travelassistant.data.preferences.FirebasePreferenceSession
import com.kltn.travelassistant.data.preferences.PreferenceOwnerKey
import com.kltn.travelassistant.data.preferences.PreferenceTokenResult
import com.kltn.travelassistant.feature.auth.domain.AuthError
import com.kltn.travelassistant.feature.auth.domain.AuthRepository
import com.kltn.travelassistant.feature.auth.domain.AuthResult
import com.kltn.travelassistant.feature.auth.domain.AuthSession
import com.kltn.travelassistant.feature.auth.domain.AuthUser
import com.kltn.travelassistant.feature.auth.domain.RegistrationResult
import com.kltn.travelassistant.feature.itinerary.domain.ItineraryCity
import com.kltn.travelassistant.feature.itinerary.domain.ItineraryDraft
import com.kltn.travelassistant.feature.itinerary.domain.ItineraryDraftItem
import com.kltn.travelassistant.feature.itinerary.domain.ItinerarySaveResult
import com.kltn.travelassistant.feature.itinerary.domain.SavedItineraryDeleteResult
import com.kltn.travelassistant.feature.itinerary.domain.SavedItineraryLibraryState
import java.time.LocalDate
import java.time.LocalTime
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.test.runTest
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class RoomSavedItineraryRepositoryTest {
    private lateinit var database: TravelAssistantDatabase
    private lateinit var auth: FakeAuthRepository
    private lateinit var session: FakeFirebaseSession
    private lateinit var scheduler: FakeScheduler
    private lateinit var repository: RoomSavedItineraryRepository

    @Before
    fun setUp() {
        val context = ApplicationProvider.getApplicationContext<Context>()
        database = Room.inMemoryDatabaseBuilder(
            context,
            TravelAssistantDatabase::class.java,
        ).allowMainThreadQueries().build()
        auth = FakeAuthRepository(authenticatedSession(UID_A))
        session = FakeFirebaseSession(PreferenceOwnerKey.fromUid(UID_A))
        scheduler = FakeScheduler()
        repository = RoomSavedItineraryRepository(
            database.itineraryDao(),
            auth,
            session,
            scheduler,
            SavedItineraryLocalCodec(),
        )
    }

    @After
    fun tearDown() {
        database.close()
    }

    @Test
    fun explicitSaveIsAtomicImmediatelyReadableAndOmitsSensitiveDraftInput() = runTest {
        assertEquals(ItinerarySaveResult.SavedLocally, repository.save(draft()))

        val library = repository.observeLibrary().first() as SavedItineraryLibraryState.Content
        val saved = library.itineraries.single()
        assertEquals(listOf("Bưu điện", "Bảo tàng"), saved.draft.items.map { it.title })
        assertEquals(listOf(0, 1), database.itineraryDao()
            .getItemsForItinerary(saved.id).map { it.position })
        val row = database.itineraryDao().getItineraryById(
            PreferenceOwnerKey.fromUid(UID_A),
            saved.id,
        )
        assertEquals("pending", row?.syncState)
        assertEquals(1L, row?.localRevision)
        assertEquals(0L, row?.serverRevision)
        assertNotEquals(UID_A, row?.accountKey)
        assertEquals(64, row?.accountKey?.length)
        assertTrue(database.itineraryDao().getItemsForItinerary(saved.id).all {
            it.notes == null && it.poiId == null && it.travelTimeMinutes == null
        })
        assertEquals(listOf(saved.id), scheduler.ids)
    }

    @Test
    fun accountSwitchAndSignOutNeverExposeAnotherAccountsRows() = runTest {
        repository.save(draft())

        auth.session.value = authenticatedSession(UID_B)
        session.ownerKey = PreferenceOwnerKey.fromUid(UID_B)
        val accountB = repository.observeLibrary().first() as SavedItineraryLibraryState.Content
        assertTrue(accountB.itineraries.isEmpty())

        auth.session.value = AuthSession.SignedOut
        session.ownerKey = null
        assertEquals(SavedItineraryLibraryState.SignedOut, repository.observeLibrary().first())
        assertEquals(ItinerarySaveResult.AuthenticationRequired, repository.save(draft()))

        auth.session.value = authenticatedSession(UID_A)
        session.ownerKey = PreferenceOwnerKey.fromUid(UID_A)
        val accountA = repository.observeLibrary().first() as SavedItineraryLibraryState.Content
        assertEquals(1, accountA.itineraries.size)
    }

    @Test
    fun localDeleteHidesContentKeepsTombstoneAndRemovesItems() = runTest {
        repository.save(draft())
        val saved = (repository.observeLibrary().first() as SavedItineraryLibraryState.Content)
            .itineraries.single()

        assertEquals(
            SavedItineraryDeleteResult.DeletedLocally,
            repository.delete(saved.id),
        )

        val library = repository.observeLibrary().first() as SavedItineraryLibraryState.Content
        assertTrue(library.itineraries.isEmpty())
        val row = database.itineraryDao().getItineraryById(
            PreferenceOwnerKey.fromUid(UID_A),
            saved.id,
        )
        assertEquals(true, row?.isDeleted)
        assertEquals(2L, row?.localRevision)
        assertEquals("pending", row?.syncState)
        assertTrue(database.itineraryDao().getItemsForItinerary(saved.id).isEmpty())
        assertEquals(listOf(saved.id, saved.id), scheduler.ids)
    }

    @Test
    fun schedulerFailureNeverRevokesSuccessfulRoomSave() = runTest {
        scheduler.shouldFail = true

        assertEquals(ItinerarySaveResult.SavedLocally, repository.save(draft()))

        val saved = (repository.observeLibrary().first() as SavedItineraryLibraryState.Content)
            .itineraries.single()
        assertEquals(
            com.kltn.travelassistant.feature.itinerary.domain.ItinerarySyncState.FAILED,
            saved.syncState,
        )
    }

    @Test
    fun staleUploadSuccessCannotClearOrResurrectANewerLocalDelete() = runTest {
        repository.save(draft())
        val saved = (repository.observeLibrary().first() as SavedItineraryLibraryState.Content)
            .itineraries.single()
        val api = MutatingApi {
            database.itineraryDao().markDeletedAndRemoveItems(
                PreferenceOwnerKey.fromUid(UID_A),
                saved.id,
                300,
            )
            ItineraryRemoteResult.Success(1)
        }
        val engine = SavedItinerarySyncEngine(
            session,
            database.itineraryDao(),
            api,
            SavedItineraryLocalCodec(),
        )

        assertEquals(
            ItinerarySyncOutcome.NEWER_LOCAL_REVISION,
            engine.synchronize(saved.id),
        )
        val tombstone = database.itineraryDao().getItineraryById(
            PreferenceOwnerKey.fromUid(UID_A),
            saved.id,
        )
        assertEquals(true, tombstone?.isDeleted)
        assertEquals("pending", tombstone?.syncState)
        assertEquals(2L, tombstone?.localRevision)
        assertEquals(1L, tombstone?.serverRevision)
        assertTrue(database.itineraryDao().getItemsForItinerary(saved.id).isEmpty())

        api.handler = { snapshot ->
            assertTrue(snapshot.deleted)
            assertEquals(1L, snapshot.serverRevision)
            ItineraryRemoteResult.Success(2)
        }
        assertEquals(ItinerarySyncOutcome.SUCCESS, engine.synchronize(saved.id))
        assertEquals(
            "synced",
            database.itineraryDao().getItineraryById(
                PreferenceOwnerKey.fromUid(UID_A),
                saved.id,
            )?.syncState,
        )
        assertNull(database.itineraryDao().getItineraryWithItems("missing", saved.id))
    }

    @Test
    fun conflictAndInvalidRemoteDataMapToStableLocalStatesWithoutDeletingContent() = runTest {
        repository.save(draft())
        val saved = (repository.observeLibrary().first() as SavedItineraryLibraryState.Content)
            .itineraries.single()
        val api = MutatingApi { ItineraryRemoteResult.Conflict }
        val engine = SavedItinerarySyncEngine(
            session,
            database.itineraryDao(),
            api,
            SavedItineraryLocalCodec(),
        )

        assertEquals(ItinerarySyncOutcome.CONFLICT, engine.synchronize(saved.id))
        assertEquals(
            "conflict",
            database.itineraryDao().getItineraryById(
                PreferenceOwnerKey.fromUid(UID_A),
                saved.id,
            )?.syncState,
        )
        assertEquals(2, database.itineraryDao().getItemsForItinerary(saved.id).size)

        database.itineraryDao().markSyncState(
            PreferenceOwnerKey.fromUid(UID_A),
            saved.id,
            1,
            "pending",
        )
        api.handler = { ItineraryRemoteResult.InvalidData }
        assertEquals(ItinerarySyncOutcome.INVALID_DATA, engine.synchronize(saved.id))
        assertEquals(
            "failed",
            database.itineraryDao().getItineraryById(
                PreferenceOwnerKey.fromUid(UID_A),
                saved.id,
            )?.syncState,
        )
        assertEquals(2, database.itineraryDao().getItemsForItinerary(saved.id).size)
    }

    private fun draft() = ItineraryDraft(
        city = ItineraryCity.HO_CHI_MINH_CITY,
        localDate = LocalDate.of(2026, 8, 1),
        timezone = "Asia/Ho_Chi_Minh",
        startLocalTime = LocalTime.of(9, 0),
        endLocalTime = LocalTime.of(17, 0),
        items = listOf(
            ItineraryDraftItem("Bưu điện", LocalTime.of(9, 0), LocalTime.of(10, 0)),
            ItineraryDraftItem("Bảo tàng", LocalTime.of(10, 30), LocalTime.of(12, 0)),
        ),
        assumptions = listOf("Đi bộ giữa các điểm gần nhau."),
        warnings = emptyList(),
    )

    private fun authenticatedSession(uid: String) = AuthSession.Authenticated(
        AuthUser(uid = uid, email = "verified@example.invalid", isEmailVerified = true),
    )

    private class FakeScheduler : ItineraryWorkScheduler {
        val ids = mutableListOf<String>()
        var shouldFail = false

        override fun enqueue(itineraryId: String) {
            ids += itineraryId
            if (shouldFail) throw IllegalStateException("scheduler unavailable")
        }
    }

    private class FakeFirebaseSession(
        var ownerKey: String?,
    ) : FirebasePreferenceSession {
        override fun currentVerifiedAccount(): ActivePreferenceAccount? =
            ownerKey?.let(::ActivePreferenceAccount)

        override suspend fun idToken(
            expectedOwnerKey: String,
            forceRefresh: Boolean,
        ) = PreferenceTokenResult.Success("ephemeral")
    }

    private class FakeAuthRepository(initial: AuthSession) : AuthRepository {
        val session = MutableStateFlow(initial)
        override fun observeSession(): Flow<AuthSession> = session
        override suspend fun register(email: String, password: String) =
            RegistrationResult.Failure(AuthError.UNKNOWN)
        override suspend fun signIn(email: String, password: String): AuthResult<AuthUser> =
            AuthResult.Failure(AuthError.UNKNOWN)
        override suspend fun signInWithGoogleIdToken(idToken: String): AuthResult<AuthUser> =
            AuthResult.Failure(AuthError.UNKNOWN)
        override suspend fun refreshVerification(): AuthResult<AuthUser> =
            AuthResult.Failure(AuthError.UNKNOWN)
        override suspend fun resendVerificationEmail(): AuthResult<Unit> =
            AuthResult.Failure(AuthError.UNKNOWN)
        override suspend fun signOut(): AuthResult<Unit> =
            AuthResult.Failure(AuthError.UNKNOWN)
    }

    private class MutatingApi(
        var handler: suspend (SavedItinerarySyncSnapshot) -> ItineraryRemoteResult,
    ) : SavedItineraryApi {
        override suspend fun synchronize(
            ownerKey: String,
            snapshot: SavedItinerarySyncSnapshot,
        ): ItineraryRemoteResult = handler(snapshot)
    }

    private companion object {
        const val UID_A = "firebase-user-a"
        const val UID_B = "firebase-user-b"
    }
}
