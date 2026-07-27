package com.kltn.travelassistant.data.packages

import androidx.room.withTransaction
import com.kltn.travelassistant.data.local.TravelAssistantDatabase
import javax.inject.Inject
import javax.inject.Singleton

enum class PackageActivationResult {
    ACTIVATED,
    ALREADY_ACTIVE,
    REJECTED_OLDER_OR_CONFLICTING,
}

fun interface PackageActivator {
    suspend fun activate(travelPackage: ValidatedTravelPackage): PackageActivationResult
}

@Singleton
class RoomPackageActivator @Inject constructor(
    private val database: TravelAssistantDatabase,
) : PackageActivator {
    override suspend fun activate(
        travelPackage: ValidatedTravelPackage,
    ): PackageActivationResult = database.withTransaction {
        val metadata = travelPackage.metadata
        val active = database.travelPackageDao().getLatestPackage(metadata.city)
        if (
            active != null &&
            active.packageId == metadata.packageId &&
            active.version == metadata.version &&
            active.manifestJson == metadata.manifestJson
        ) {
            return@withTransaction PackageActivationResult.ALREADY_ACTIVE
        }
        if (
            active != null &&
            (
                metadata.publishedAtEpochMillis < active.publishedAtEpochMillis ||
                    (
                        metadata.publishedAtEpochMillis == active.publishedAtEpochMillis &&
                            (
                                metadata.packageId != active.packageId ||
                                    metadata.version != active.version
                                )
                        )
                )
        ) {
            return@withTransaction PackageActivationResult.REJECTED_OLDER_OR_CONFLICTING
        }

        database.poiContentDao().apply {
            deletePoisByCity(metadata.city)
            deleteCultureByCity(metadata.city)
            upsertPois(travelPackage.pois)
            if (travelPackage.aliases.isNotEmpty()) upsertAliases(travelPackage.aliases)
            if (travelPackage.menuItems.isNotEmpty()) upsertMenuItems(travelPackage.menuItems)
            if (travelPackage.narrations.isNotEmpty()) upsertNarrations(travelPackage.narrations)
        }
        database.travelPackageDao().apply {
            deletePackagesByCity(metadata.city)
            upsertPackage(metadata)
        }
        PackageActivationResult.ACTIVATED
    }
}
