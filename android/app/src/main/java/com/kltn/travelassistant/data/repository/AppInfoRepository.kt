package com.kltn.travelassistant.data.repository

import kotlinx.coroutines.flow.StateFlow

interface AppInfoRepository {
    val appName: StateFlow<String>
}
