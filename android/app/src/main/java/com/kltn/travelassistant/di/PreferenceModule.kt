package com.kltn.travelassistant.di

import android.content.Context
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.PreferenceDataStoreFactory
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.preferencesDataStoreFile
import com.kltn.travelassistant.data.preferences.BackendEndpointProvider
import com.kltn.travelassistant.data.preferences.BuildConfigBackendEndpointProvider
import com.kltn.travelassistant.data.preferences.DataStorePreferenceLocalStore
import com.kltn.travelassistant.data.preferences.DefaultFirebasePreferenceSession
import com.kltn.travelassistant.data.preferences.DefaultPreferenceRepository
import com.kltn.travelassistant.data.preferences.FirebasePreferenceSession
import com.kltn.travelassistant.data.preferences.OkHttpPreferenceApi
import com.kltn.travelassistant.data.preferences.PreferenceApi
import com.kltn.travelassistant.data.preferences.PreferenceDocumentCodec
import com.kltn.travelassistant.data.preferences.PreferenceLocalStore
import com.kltn.travelassistant.data.preferences.PreferenceWorkScheduler
import com.kltn.travelassistant.data.preferences.WorkManagerPreferenceScheduler
import com.kltn.travelassistant.feature.preferences.domain.PreferenceRepository
import dagger.Binds
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.android.qualifiers.ApplicationContext
import dagger.hilt.components.SingletonComponent
import javax.inject.Singleton
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob

@Module
@InstallIn(SingletonComponent::class)
internal abstract class PreferenceModule {
    @Binds
    @Singleton
    abstract fun bindBackendEndpointProvider(
        implementation: BuildConfigBackendEndpointProvider,
    ): BackendEndpointProvider

    @Binds
    @Singleton
    abstract fun bindFirebasePreferenceSession(
        implementation: DefaultFirebasePreferenceSession,
    ): FirebasePreferenceSession

    @Binds
    @Singleton
    abstract fun bindPreferenceApi(
        implementation: OkHttpPreferenceApi,
    ): PreferenceApi

    @Binds
    @Singleton
    abstract fun bindPreferenceScheduler(
        implementation: WorkManagerPreferenceScheduler,
    ): PreferenceWorkScheduler

    @Binds
    @Singleton
    abstract fun bindPreferenceRepository(
        implementation: DefaultPreferenceRepository,
    ): PreferenceRepository

    companion object {
        private const val PREFERENCE_DATASTORE_FILE = "user_preferences"

        @Provides
        @Singleton
        fun providePreferenceCodec(): PreferenceDocumentCodec =
            PreferenceDocumentCodec()

        @Provides
        @Singleton
        fun providePreferenceDataStore(
            @ApplicationContext context: Context,
        ): DataStore<Preferences> = PreferenceDataStoreFactory.create(
            scope = CoroutineScope(SupervisorJob() + Dispatchers.IO),
            produceFile = {
                context.preferencesDataStoreFile(PREFERENCE_DATASTORE_FILE)
            },
        )

        @Provides
        @Singleton
        fun providePreferenceLocalStore(
            dataStore: DataStore<Preferences>,
            codec: PreferenceDocumentCodec,
        ): PreferenceLocalStore = DataStorePreferenceLocalStore(
            dataStore = dataStore,
            codec = codec,
        )
    }
}

