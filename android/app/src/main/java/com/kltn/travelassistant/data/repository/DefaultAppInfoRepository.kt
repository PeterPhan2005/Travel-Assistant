package com.kltn.travelassistant.data.repository

import javax.inject.Inject
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow

class DefaultAppInfoRepository @Inject constructor() : AppInfoRepository {
    private val mutableAppName = MutableStateFlow("Travel Assistant")

    override val appName: StateFlow<String> = mutableAppName.asStateFlow()
}
