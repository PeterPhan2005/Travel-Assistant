package com.kltn.travelassistant.navigation.external

import android.content.ActivityNotFoundException
import android.content.Context
import android.content.Intent
import dagger.hilt.android.qualifiers.ApplicationContext
import javax.inject.Inject
import javax.inject.Singleton

interface ExternalMapActivityGateway {
    fun canOpen(intent: Intent): Boolean

    @Throws(ActivityNotFoundException::class)
    fun open(intent: Intent)
}

@Singleton
class AndroidExternalMapActivityGateway @Inject constructor(
    @param:ApplicationContext private val context: Context,
) : ExternalMapActivityGateway {
    override fun canOpen(intent: Intent): Boolean =
        intent.resolveActivity(context.packageManager) != null

    override fun open(intent: Intent) = context.startActivity(intent)
}
