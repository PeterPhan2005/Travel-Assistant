package com.kltn.travelassistant.data.seed

import android.content.Context
import dagger.hilt.android.qualifiers.ApplicationContext
import javax.inject.Inject
import javax.inject.Singleton
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

fun interface SeedSource {
    suspend fun read(): String
}

@Singleton
class BundledHcmcSeedSource @Inject constructor(
    @param:ApplicationContext private val context: Context,
) : SeedSource {
    override suspend fun read(): String = withContext(Dispatchers.IO) {
        context.assets.open(ASSET_PATH).bufferedReader().use { it.readText() }
    }

    companion object {
        const val ASSET_PATH = "seeds/hcmc_seed_v1.json"
    }
}
