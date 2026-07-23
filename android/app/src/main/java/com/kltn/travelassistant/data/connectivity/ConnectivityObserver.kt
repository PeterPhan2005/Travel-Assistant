package com.kltn.travelassistant.data.connectivity

import kotlinx.coroutines.flow.Flow

enum class ConnectivityStatus {
    UNKNOWN,
    ONLINE,
    OFFLINE,
}

interface ConnectivityObserver {
    val status: Flow<ConnectivityStatus>
}
