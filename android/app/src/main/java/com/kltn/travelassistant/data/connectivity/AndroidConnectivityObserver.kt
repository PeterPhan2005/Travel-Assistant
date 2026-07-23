package com.kltn.travelassistant.data.connectivity

import android.content.Context
import android.net.ConnectivityManager
import android.net.Network
import android.net.NetworkCapabilities
import dagger.hilt.android.qualifiers.ApplicationContext
import javax.inject.Inject
import javax.inject.Singleton
import kotlinx.coroutines.channels.awaitClose
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.callbackFlow
import kotlinx.coroutines.flow.distinctUntilChanged

internal fun interface ConnectivityRegistration {
    fun unregister()
}

internal interface ConnectivityManagerGateway {
    fun currentStatus(): ConnectivityStatus

    fun register(onNetworkChanged: () -> Unit): ConnectivityRegistration
}

@Singleton
internal class AndroidConnectivityManagerGateway @Inject constructor(
    @ApplicationContext context: Context,
) : ConnectivityManagerGateway {
    private val connectivityManager = context.getSystemService(ConnectivityManager::class.java)

    override fun currentStatus(): ConnectivityStatus = try {
        connectivityManager
            .getNetworkCapabilities(connectivityManager.activeNetwork)
            .toConnectivityStatus()
    } catch (_: SecurityException) {
        ConnectivityStatus.UNKNOWN
    } catch (_: RuntimeException) {
        ConnectivityStatus.UNKNOWN
    }

    override fun register(onNetworkChanged: () -> Unit): ConnectivityRegistration {
        val callback = object : ConnectivityManager.NetworkCallback() {
            override fun onAvailable(network: Network) = onNetworkChanged()

            override fun onCapabilitiesChanged(
                network: Network,
                networkCapabilities: NetworkCapabilities,
            ) = onNetworkChanged()

            override fun onLost(network: Network) = onNetworkChanged()

            override fun onUnavailable() = onNetworkChanged()
        }
        connectivityManager.registerDefaultNetworkCallback(callback)
        return ConnectivityRegistration {
            try {
                connectivityManager.unregisterNetworkCallback(callback)
            } catch (_: IllegalArgumentException) {
                // A duplicate platform cleanup must not crash application teardown.
            } catch (_: SecurityException) {
                // Permission or platform-state changes during teardown are recoverable.
            } catch (_: RuntimeException) {
                // Connectivity teardown is best-effort and must not crash the app.
            }
        }
    }
}

@Singleton
internal class DefaultConnectivityObserver @Inject constructor(
    private val gateway: ConnectivityManagerGateway,
) : ConnectivityObserver {
    override val status: Flow<ConnectivityStatus> = callbackFlow {
        fun emitCurrentStatus() {
            val current = try {
                gateway.currentStatus()
            } catch (_: SecurityException) {
                ConnectivityStatus.UNKNOWN
            } catch (_: RuntimeException) {
                ConnectivityStatus.UNKNOWN
            }
            trySend(current)
        }

        emitCurrentStatus()
        val registration = try {
            gateway.register(::emitCurrentStatus)
        } catch (_: SecurityException) {
            trySend(ConnectivityStatus.UNKNOWN)
            null
        } catch (_: RuntimeException) {
            trySend(ConnectivityStatus.UNKNOWN)
            null
        }
        if (registration != null) {
            emitCurrentStatus()
        }

        awaitClose {
            registration?.unregister()
        }
    }.distinctUntilChanged()
}

internal fun NetworkCapabilities?.toConnectivityStatus(): ConnectivityStatus {
    return classifyConnectivity(
        hasInternetCapability = this?.hasCapability(
            NetworkCapabilities.NET_CAPABILITY_INTERNET,
        ) == true,
        hasValidatedCapability = this?.hasCapability(
            NetworkCapabilities.NET_CAPABILITY_VALIDATED,
        ) == true,
    )
}

internal fun classifyConnectivity(
    hasInternetCapability: Boolean,
    hasValidatedCapability: Boolean,
): ConnectivityStatus =
    if (hasInternetCapability && hasValidatedCapability) {
        ConnectivityStatus.ONLINE
    } else {
        ConnectivityStatus.OFFLINE
    }
