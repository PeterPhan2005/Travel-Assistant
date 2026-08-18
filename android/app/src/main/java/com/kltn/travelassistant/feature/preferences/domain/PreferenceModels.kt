package com.kltn.travelassistant.feature.preferences.domain

import kotlinx.coroutines.flow.StateFlow
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonNull
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive

const val PREFERENCE_SCHEMA_VERSION = 1
const val TRAVEL_PREFERENCE_SCHEMA_VERSION = 2
const val MAX_TRAVEL_INTERESTS = 5

data class PreferenceDocument(
    val schemaVersion: Int = PREFERENCE_SCHEMA_VERSION,
    val preferences: JsonObject = JsonObject(emptyMap()),
)

enum class TravelInterest(val wireValue: String) {
    FOOD_AND_CAFES("food_and_cafes"),
    CULTURE_AND_HISTORY("culture_and_history"),
    SCENIC_AND_LANDMARKS("scenic_and_landmarks"),
    NATURE_AND_OUTDOORS("nature_and_outdoors"),
    LOCAL_LIFE_AND_MARKETS("local_life_and_markets"),
    ENTERTAINMENT_AND_NIGHTLIFE("entertainment_and_nightlife"),
    FAMILY_ACTIVITIES("family_activities"),
    WELLNESS_AND_RELAXATION("wellness_and_relaxation"),
    ;

    companion object {
        fun fromWire(value: String): TravelInterest? = entries.find { it.wireValue == value }
    }
}

enum class TravelPace(val wireValue: String) {
    RELAXED("relaxed"),
    BALANCED("balanced"),
    ACTIVE("active"),
    ;

    companion object {
        fun fromWire(value: String): TravelPace? = entries.find { it.wireValue == value }
    }
}

enum class BudgetPreference(val wireValue: String) {
    BUDGET("budget"),
    MODERATE("moderate"),
    PREMIUM("premium"),
    ;

    companion object {
        fun fromWire(value: String): BudgetPreference? = entries.find { it.wireValue == value }
    }
}

data class TravelPreferenceProfile(
    val interests: Set<TravelInterest> = emptySet(),
    val pace: TravelPace? = null,
    val budgetPreference: BudgetPreference? = null,
) {
    init {
        require(interests.size <= MAX_TRAVEL_INTERESTS)
    }

    fun toDocument(): PreferenceDocument = PreferenceDocument(
        schemaVersion = TRAVEL_PREFERENCE_SCHEMA_VERSION,
        preferences = JsonObject(
            mapOf(
                "interests" to JsonArray(
                    TravelInterest.entries
                        .filter(interests::contains)
                        .map { JsonPrimitive(it.wireValue) },
                ),
                "pace" to pace?.let { JsonPrimitive(it.wireValue) }.orJsonNull(),
                "budget_preference" to budgetPreference
                    ?.let { JsonPrimitive(it.wireValue) }
                    .orJsonNull(),
            ),
        ),
    )
}

fun PreferenceDocument.toTravelPreferenceProfileOrNull(): TravelPreferenceProfile? {
    if (
        schemaVersion != TRAVEL_PREFERENCE_SCHEMA_VERSION ||
        preferences.keys != setOf("interests", "pace", "budget_preference")
    ) {
        return null
    }
    val interestsArray = preferences["interests"] as? JsonArray ?: return null
    val interests = interestsArray.map { element ->
        val primitive = element as? JsonPrimitive ?: return null
        if (!primitive.isString) return null
        TravelInterest.fromWire(primitive.content) ?: return null
    }
    if (interests.size > MAX_TRAVEL_INTERESTS || interests.size != interests.toSet().size) {
        return null
    }
    val pace = parseNullableEnum(preferences["pace"], TravelPace::fromWire) ?: return null
    val budget = parseNullableEnum(
        preferences["budget_preference"],
        BudgetPreference::fromWire,
    ) ?: return null
    return TravelPreferenceProfile(
        interests = interests.toSet(),
        pace = pace.value,
        budgetPreference = budget.value,
    )
}

private data class NullableEnum<T>(val value: T?)

private fun <T> parseNullableEnum(
    element: kotlinx.serialization.json.JsonElement?,
    parse: (String) -> T?,
): NullableEnum<T>? {
    if (element == JsonNull) return NullableEnum(null)
    val primitive = element as? JsonPrimitive ?: return null
    if (!primitive.isString) return null
    return parse(primitive.content)?.let(::NullableEnum)
}

private fun JsonPrimitive?.orJsonNull(): kotlinx.serialization.json.JsonElement = this ?: JsonNull

sealed interface PreferenceSyncState {
    data object SignedOut : PreferenceSyncState

    data object LoadingLocal : PreferenceSyncState

    data class LocalCurrent(val document: PreferenceDocument) : PreferenceSyncState

    data class PendingOffline(val document: PreferenceDocument) : PreferenceSyncState

    data class Synchronizing(val document: PreferenceDocument) : PreferenceSyncState

    data class Synchronized(
        val document: PreferenceDocument,
        val serverUpdatedAt: String,
    ) : PreferenceSyncState

    data class RetryableFailure(val document: PreferenceDocument) : PreferenceSyncState

    data object AuthenticationFailure : PreferenceSyncState

    data object InvalidDocument : PreferenceSyncState
}

sealed interface PreferenceUpdateResult {
    data object SavedAndQueued : PreferenceUpdateResult

    data object SignedOut : PreferenceUpdateResult

    data object InvalidDocument : PreferenceUpdateResult

    data object StorageFailure : PreferenceUpdateResult
}

interface PreferenceRepository {
    val state: StateFlow<PreferenceSyncState>

    suspend fun updateLocal(document: PreferenceDocument): PreferenceUpdateResult

    fun refresh()

    fun retry()
}

fun PreferenceSyncState.documentOrNull(): PreferenceDocument? = when (this) {
    is PreferenceSyncState.LocalCurrent -> document
    is PreferenceSyncState.PendingOffline -> document
    is PreferenceSyncState.Synchronizing -> document
    is PreferenceSyncState.Synchronized -> document
    is PreferenceSyncState.RetryableFailure -> document
    PreferenceSyncState.SignedOut,
    PreferenceSyncState.LoadingLocal,
    PreferenceSyncState.AuthenticationFailure,
    PreferenceSyncState.InvalidDocument,
    -> null
}
