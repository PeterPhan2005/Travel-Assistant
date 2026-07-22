package com.kltn.travelassistant.data.location

import android.Manifest
import android.annotation.SuppressLint
import android.content.Context
import android.content.pm.PackageManager
import android.location.Location
import android.location.LocationManager
import androidx.core.content.ContextCompat
import androidx.core.location.LocationManagerCompat
import androidx.core.os.CancellationSignal
import dagger.hilt.android.qualifiers.ApplicationContext
import javax.inject.Inject
import javax.inject.Singleton
import kotlin.coroutines.resume
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.suspendCancellableCoroutine
import kotlinx.coroutines.withTimeoutOrNull

@Singleton
class AndroidLocationClient @Inject constructor(
    @param:ApplicationContext private val context: Context,
) : LocationClient {
    private val locationManager: LocationManager =
        context.getSystemService(LocationManager::class.java)

    override suspend fun getCurrentLocation(): LocationAcquisitionResult {
        val hasFinePermission = context.hasPermission(Manifest.permission.ACCESS_FINE_LOCATION)
        val hasCoarsePermission = context.hasPermission(Manifest.permission.ACCESS_COARSE_LOCATION)
        if (!hasFinePermission && !hasCoarsePermission) {
            return LocationAcquisitionResult.PermissionDenied
        }

        return try {
            val provider = selectEnabledProvider(hasFinePermission)
                ?: return LocationAcquisitionResult.ProviderUnavailable
            withTimeoutOrNull(LOCATION_TIMEOUT_MILLIS) {
                awaitCurrentLocation(provider)
            } ?: LocationAcquisitionResult.Timeout
        } catch (_: SecurityException) {
            LocationAcquisitionResult.PermissionDenied
        } catch (_: IllegalArgumentException) {
            LocationAcquisitionResult.ProviderUnavailable
        } catch (exception: CancellationException) {
            throw exception
        } catch (_: Exception) {
            LocationAcquisitionResult.Failure
        }
    }

    private fun selectEnabledProvider(hasFinePermission: Boolean): String? {
        val availableProviders = locationManager.allProviders
        val candidates = buildList {
            if (hasFinePermission) {
                add(LocationManager.GPS_PROVIDER)
            }
            add(FUSED_PROVIDER)
            add(LocationManager.NETWORK_PROVIDER)
        }
        return candidates.firstOrNull { provider ->
            provider in availableProviders && locationManager.isProviderEnabled(provider)
        }
    }

    @SuppressLint("MissingPermission")
    private suspend fun awaitCurrentLocation(provider: String): LocationAcquisitionResult =
        suspendCancellableCoroutine { continuation ->
            val cancellationSignal = CancellationSignal()
            continuation.invokeOnCancellation { cancellationSignal.cancel() }
            LocationManagerCompat.getCurrentLocation(
                locationManager,
                provider,
                cancellationSignal,
                ContextCompat.getMainExecutor(context),
            ) { location ->
                if (!continuation.isActive) return@getCurrentLocation
                continuation.resume(location.toAcquisitionResult())
            }
        }

    private fun Location?.toAcquisitionResult(): LocationAcquisitionResult =
        if (this == null) {
            LocationAcquisitionResult.ProviderUnavailable
        } else {
            LocationAcquisitionResult.Success(
                location = DeviceLocation(
                    latitude = latitude,
                    longitude = longitude,
                    accuracyMeters = accuracy.takeIf { hasAccuracy() },
                    capturedAtEpochMillis = time.takeIf { it > 0L },
                ),
            )
        }

    private fun Context.hasPermission(permission: String): Boolean =
        ContextCompat.checkSelfPermission(this, permission) == PackageManager.PERMISSION_GRANTED

    private companion object {
        const val FUSED_PROVIDER = "fused"
        const val LOCATION_TIMEOUT_MILLIS = 15_000L
    }
}
