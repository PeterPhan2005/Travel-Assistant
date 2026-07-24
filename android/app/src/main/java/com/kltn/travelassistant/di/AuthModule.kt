package com.kltn.travelassistant.di

import com.google.firebase.auth.FirebaseAuth
import com.kltn.travelassistant.data.auth.AuthGateway
import com.kltn.travelassistant.data.auth.FirebaseAuthGateway
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

    companion object {
        @Provides
        @Singleton
        fun provideFirebaseAuth(): FirebaseAuth = FirebaseAuth.getInstance()
    }
}
