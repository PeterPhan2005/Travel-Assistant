# Android Instructions

- Language: Kotlin.
- UI: Jetpack Compose + Material 3.
- Architecture: UI, domain where justified, data; repositories are the source of truth.
- State: immutable UI state exposed by ViewModel using StateFlow.
- Async: Kotlin coroutines and Flow.
- DI: Hilt.
- Local structured data: Room.
- Preferences/tiny settings: DataStore.
- Network: Retrofit/OkHttp with Kotlin serialization.
- Auth: Firebase Authentication.
- Never call OpenAI or third-party POI APIs directly from the app when an API key would be exposed.
- Location permission is requested only at the feature point that needs it.
- Microphone permission is requested only when voice input is activated.
- Offline behavior must be explicit in UI state and tests.
- No business logic in composables.
