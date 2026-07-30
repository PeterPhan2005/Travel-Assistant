package com.kltn.travelassistant.di

import com.kltn.travelassistant.feature.assistant.data.AndroidSpeechRecognitionEngine
import com.kltn.travelassistant.feature.assistant.domain.SpeechRecognitionEngine
import dagger.Binds
import dagger.Module
import dagger.hilt.InstallIn
import dagger.hilt.android.components.ViewModelComponent
import dagger.hilt.android.scopes.ViewModelScoped

@Module
@InstallIn(ViewModelComponent::class)
abstract class SpeechRecognitionModule {
    @Binds
    @ViewModelScoped
    abstract fun bindSpeechRecognitionEngine(
        implementation: AndroidSpeechRecognitionEngine,
    ): SpeechRecognitionEngine
}
