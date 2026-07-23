package com.kltn.travelassistant.data.connectivity

import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.flow.toList
import kotlinx.coroutines.launch
import kotlinx.coroutines.test.UnconfinedTestDispatcher
import kotlinx.coroutines.test.runCurrent
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Test

@OptIn(ExperimentalCoroutinesApi::class)
class DefaultConnectivityObserverTest {
    @Test
    fun emitsInitialStateAndCallbackChangesThenUnregistersOnCancellation() = runTest {
        val gateway = FakeConnectivityManagerGateway(ConnectivityStatus.OFFLINE)
        val observer = DefaultConnectivityObserver(gateway)
        val emissions = mutableListOf<ConnectivityStatus>()
        val collection = backgroundScope.launch(UnconfinedTestDispatcher(testScheduler)) {
            observer.status.toList(emissions)
        }

        assertEquals(listOf(ConnectivityStatus.OFFLINE), emissions)

        gateway.emit(ConnectivityStatus.ONLINE)
        gateway.emit(ConnectivityStatus.OFFLINE)
        assertEquals(
            listOf(
                ConnectivityStatus.OFFLINE,
                ConnectivityStatus.ONLINE,
                ConnectivityStatus.OFFLINE,
            ),
            emissions,
        )

        collection.cancel()
        runCurrent()
        assertEquals(1, gateway.unregisterCount)
    }

    @Test
    fun gatewayFailuresBecomeControlledUnknownState() = runTest {
        val gateway = ThrowingConnectivityManagerGateway()
        val observer = DefaultConnectivityObserver(gateway)
        val emissions = mutableListOf<ConnectivityStatus>()
        val collection = backgroundScope.launch(UnconfinedTestDispatcher(testScheduler)) {
            observer.status.toList(emissions)
        }

        assertEquals(listOf(ConnectivityStatus.UNKNOWN), emissions)

        collection.cancel()
        runCurrent()
        assertEquals(0, gateway.unregisterCount)
    }

    private class FakeConnectivityManagerGateway(
        initialStatus: ConnectivityStatus,
    ) : ConnectivityManagerGateway {
        private var currentStatus = initialStatus
        private var callback: (() -> Unit)? = null
        var unregisterCount = 0
            private set

        override fun currentStatus(): ConnectivityStatus = currentStatus

        override fun register(onNetworkChanged: () -> Unit): ConnectivityRegistration {
            callback = onNetworkChanged
            return ConnectivityRegistration {
                unregisterCount += 1
                callback = null
            }
        }

        fun emit(status: ConnectivityStatus) {
            currentStatus = status
            callback?.invoke()
        }
    }

    private class ThrowingConnectivityManagerGateway : ConnectivityManagerGateway {
        var unregisterCount = 0
            private set

        override fun currentStatus(): ConnectivityStatus = error("current status unavailable")

        override fun register(onNetworkChanged: () -> Unit): ConnectivityRegistration =
            error("registration unavailable")
    }
}
