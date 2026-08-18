package com.kltn.travelassistant.feature.preferences.presentation

import com.kltn.travelassistant.feature.preferences.domain.PreferenceDocument
import com.kltn.travelassistant.feature.preferences.domain.PreferenceRepository
import com.kltn.travelassistant.feature.preferences.domain.PreferenceSyncState
import com.kltn.travelassistant.feature.preferences.domain.PreferenceUpdateResult
import com.kltn.travelassistant.feature.preferences.domain.TravelInterest
import com.kltn.travelassistant.feature.preferences.domain.TravelPace
import com.kltn.travelassistant.feature.preferences.domain.TravelPreferenceProfile
import com.kltn.travelassistant.feature.preferences.domain.toTravelPreferenceProfileOrNull
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.advanceUntilIdle
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.runCurrent
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.test.setMain
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test

@OptIn(ExperimentalCoroutinesApi::class)
class PreferenceProfileViewModelTest {
    private val dispatcher = StandardTestDispatcher()

    @Before
    fun setUp() = Dispatchers.setMain(dispatcher)

    @After
    fun tearDown() = Dispatchers.resetMain()

    @Test
    fun signedOutHidesProfileAndAccountSwitchReplacesVisibleValues() = runTest(dispatcher) {
        val repository = FakePreferenceRepository()
        val viewModel = PreferenceProfileViewModel(repository)
        runCurrent()

        assertFalse(viewModel.uiState.value.isVisible)
        repository.emit(profile(TravelInterest.FOOD_AND_CAFES))
        runCurrent()
        assertEquals(
            setOf(TravelInterest.FOOD_AND_CAFES),
            viewModel.uiState.value.savedProfile.interests,
        )

        repository.state.value = PreferenceSyncState.SignedOut
        runCurrent()
        assertFalse(viewModel.uiState.value.isVisible)
        repository.emit(profile(TravelInterest.CULTURE_AND_HISTORY))
        runCurrent()

        assertEquals(
            setOf(TravelInterest.CULTURE_AND_HISTORY),
            viewModel.uiState.value.savedProfile.interests,
        )
        assertFalse(viewModel.uiState.value.savedProfile.interests.contains(TravelInterest.FOOD_AND_CAFES))
    }

    @Test
    fun editLimitSaveAndExplicitResetWriteCompleteSchemaV2Documents() = runTest(dispatcher) {
        val repository = FakePreferenceRepository()
        repository.emit(TravelPreferenceProfile())
        val viewModel = PreferenceProfileViewModel(repository)
        runCurrent()
        viewModel.beginEdit()
        TravelInterest.entries.take(6).forEach(viewModel::toggleInterest)

        assertEquals(5, viewModel.uiState.value.draftProfile.interests.size)
        assertEquals(
            PreferenceProfileMessage.MAXIMUM_INTERESTS,
            viewModel.uiState.value.message,
        )
        viewModel.selectPace(TravelPace.ACTIVE)
        viewModel.save()
        advanceUntilIdle()

        assertEquals(2, repository.updates.single().schemaVersion)
        assertEquals(
            TravelPace.ACTIVE,
            viewModel.uiState.value.savedProfile.pace,
        )
        viewModel.requestReset()
        assertTrue(viewModel.uiState.value.showResetConfirmation)
        viewModel.confirmReset()
        advanceUntilIdle()

        assertEquals(2, repository.updates.last().schemaVersion)
        assertEquals(
            TravelPreferenceProfile(),
            repository.updates.last().toTravelPreferenceProfileOrNull(),
        )
    }

    @Test
    fun pendingOfflineStateKeepsEditableLocalDocument() = runTest(dispatcher) {
        val repository = FakePreferenceRepository()
        val document = profile(TravelInterest.NATURE_AND_OUTDOORS).toDocument()
        repository.state.value = PreferenceSyncState.PendingOffline(document)
        val viewModel = PreferenceProfileViewModel(repository)
        runCurrent()

        assertEquals(PreferenceProfileStatus.PENDING_OFFLINE, viewModel.uiState.value.status)
        assertTrue(viewModel.uiState.value.isVisible)
        assertEquals(
            setOf(TravelInterest.NATURE_AND_OUTDOORS),
            viewModel.uiState.value.savedProfile.interests,
        )
    }

    private fun profile(interest: TravelInterest) = TravelPreferenceProfile(
        interests = setOf(interest),
    )

    private class FakePreferenceRepository : PreferenceRepository {
        override val state = MutableStateFlow<PreferenceSyncState>(PreferenceSyncState.SignedOut)
        val updates = mutableListOf<PreferenceDocument>()

        fun emit(profile: TravelPreferenceProfile) {
            state.value = PreferenceSyncState.LocalCurrent(profile.toDocument())
        }

        override suspend fun updateLocal(document: PreferenceDocument): PreferenceUpdateResult {
            updates += document
            state.value = PreferenceSyncState.PendingOffline(document)
            return PreferenceUpdateResult.SavedAndQueued
        }

        override fun refresh() = Unit

        override fun retry() = Unit
    }
}
