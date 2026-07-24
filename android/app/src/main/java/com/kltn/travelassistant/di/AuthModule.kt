package com.kltn.travelassistant.di

import com.google.firebase.auth.FirebaseAuth
import com.kltn.travelassistant.data.auth.AuthGateway
import com.kltn.travelassistant.data.auth.AndroidGoogleCredentialAcquirer
import com.kltn.travelassistant.data.auth.CredentialStateClearer
import com.kltn.travelassistant.data.auth.DefaultGoogleCredentialCoordinator
import com.kltn.travelassistant.data.auth.DefaultGoogleIdTokenParser
import com.kltn.travelassistant.data.auth.FirebaseAuthGateway
import com.kltn.travelassistant.data.auth.GeneratedGoogleClientIdProvider
import com.kltn.travelassistant.data.auth.GoogleClientIdProvider
import com.kltn.travelassistant.data.auth.GoogleCredentialAcquirer
import com.kltn.travelassistant.data.auth.GoogleCredentialCoordinator
import com.kltn.travelassistant.data.auth.GoogleIdTokenParser
import com.kltn.travelassistant.data.repository.FirebaseAuthRepository
import com.kltn.travelassistant.feature.auth.domain.AuthRepository
import dagger.Binds
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.components.SingletonComponent
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
abstract class AuthModule {
    @Binds
    @Singleton
    abstract fun bindAuthGateway(
        implementation: FirebaseAuthGateway,
    ): AuthGateway

    @Binds
    @Singleton
    abstract fun bindAuthRepository(
        implementation: FirebaseAuthRepository,
    ): AuthRepository

    @Binds
    @Singleton
    internal abstract fun bindGoogleCredentialAcquirer(
        implementation: AndroidGoogleCredentialAcquirer,
    ): GoogleCredentialAcquirer

    @Binds
    @Singleton
    internal abstract fun bindGoogleCredentialCoordinator(
        implementation: DefaultGoogleCredentialCoordinator,
    ): GoogleCredentialCoordinator

    @Binds
    internal abstract fun bindGoogleClientIdProvider(
        implementation: GeneratedGoogleClientIdProvider,
    ): GoogleClientIdProvider

    @Binds
    internal abstract fun bindGoogleIdTokenParser(
        implementation: DefaultGoogleIdTokenParser,
    ): GoogleIdTokenParser

    companion object {
        @Provides
        @Singleton
        fun provideFirebaseAuth(): FirebaseAuth = FirebaseAuth.getInstance()

        @Provides
        @Singleton
        fun provideCredentialStateClearer(
            coordinator: GoogleCredentialCoordinator,
        ): CredentialStateClearer = coordinator
    }
}
