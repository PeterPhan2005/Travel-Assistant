import java.net.URI

plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.hilt.android)
    alias(libs.plugins.kotlin.compose)
    alias(libs.plugins.kotlin.serialization)
    alias(libs.plugins.ksp)
    alias(libs.plugins.androidx.room)
    alias(libs.plugins.google.services)
}

fun validateDebugBackendBaseUrl(raw: String): String {
    require(raw.none(Char::isISOControl)) {
        "Debug backend base URL must not contain control characters."
    }
    val uri = runCatching { URI(raw) }.getOrElse {
        throw GradleException("Debug backend base URL must be a valid absolute URL.")
    }
    require(
        uri.isAbsolute &&
            uri.host != null &&
            uri.rawUserInfo == null &&
            uri.rawQuery == null &&
            uri.rawFragment == null &&
            (uri.rawPath.isNullOrEmpty() || uri.rawPath == "/") &&
            uri.port != 0 &&
            uri.port <= 65_535,
    ) {
        "Debug backend base URL must have an origin-only root path."
    }
    val scheme = uri.scheme.lowercase()
    require(
        scheme == "https" ||
            (
                scheme == "http" &&
                    uri.host in setOf("10.0.2.2", "127.0.0.1")
                ),
    ) {
        "Cleartext debug backend URL must use 10.0.2.2 or 127.0.0.1."
    }
    return raw
}

fun String.asBuildConfigStringLiteral(): String =
    "\"${replace("\\", "\\\\").replace("\"", "\\\"")}\""

val debugBackendBaseUrl = validateDebugBackendBaseUrl(
    providers.gradleProperty("travelAssistantDebugBackendBaseUrl")
        .getOrElse("http://10.0.2.2:8000/"),
)

android {
    namespace = "com.kltn.travelassistant"
    compileSdk {
        version = release(36) {
            minorApiLevel = 1
        }
    }

    defaultConfig {
        applicationId = "com.kltn.travelassistant"
        minSdk = 26
        targetSdk = 36
        versionCode = 1
        versionName = "1.0"

        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
    }

    buildTypes {
        debug {
            buildConfigField(
                "String",
                "BACKEND_BASE_URL",
                debugBackendBaseUrl.asBuildConfigStringLiteral(),
            )
            buildConfigField(
                "String",
                "HCMC_PACKAGE_MANIFEST_URL",
                "\"http://10.0.2.2:8081/hcmc-starter-v1-1.0.0.manifest.json\"",
            )
        }
        release {
            buildConfigField("String", "BACKEND_BASE_URL", "\"\"")
            buildConfigField("String", "HCMC_PACKAGE_MANIFEST_URL", "\"\"")
            optimization {
                enable = false
            }
        }
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    buildFeatures {
        buildConfig = true
        compose = true
    }
    room {
        schemaDirectory("$projectDir/schemas")
    }
}

dependencies {
    implementation(platform(libs.androidx.compose.bom))
    implementation(platform(libs.firebase.bom))
    implementation(libs.androidx.activity.compose)
    implementation(libs.androidx.credentials)
    implementation(libs.androidx.credentials.play.services.auth)
    implementation(libs.androidx.datastore.preferences)
    implementation(libs.androidx.compose.material.icons.core)
    implementation(libs.androidx.compose.material3)
    implementation(libs.androidx.compose.ui)
    implementation(libs.androidx.compose.ui.graphics)
    implementation(libs.androidx.compose.ui.tooling.preview)
    implementation(libs.androidx.core.ktx)
    implementation(libs.androidx.lifecycle.runtime.ktx)
    implementation(libs.androidx.lifecycle.runtime.compose)
    implementation(libs.androidx.navigation.compose)
    implementation(libs.androidx.room.ktx)
    implementation(libs.androidx.room.runtime)
    implementation(libs.hilt.android)
    implementation(libs.androidx.hilt.navigation.compose)
    implementation(libs.androidx.hilt.work)
    implementation(libs.kotlinx.serialization.json)
    implementation(libs.androidx.work.runtime)
    implementation(libs.okhttp)
    implementation(libs.firebase.auth)
    implementation(libs.googleid)
    ksp(libs.hilt.compiler)
    ksp(libs.androidx.hilt.compiler)
    ksp(libs.androidx.room.compiler)
    testImplementation(libs.junit)
    testImplementation(libs.kotlinx.coroutines.test)
    testImplementation(libs.mockwebserver)
    androidTestImplementation(platform(libs.androidx.compose.bom))
    androidTestImplementation(libs.androidx.compose.ui.test.junit4)
    androidTestImplementation(libs.androidx.espresso.core)
    androidTestImplementation(libs.androidx.junit)
    androidTestImplementation(libs.androidx.room.testing)
    androidTestImplementation(libs.androidx.work.testing)
    androidTestImplementation(libs.kotlinx.coroutines.test)
    debugImplementation(libs.androidx.compose.ui.test.manifest)
    debugImplementation(libs.androidx.compose.ui.tooling)
}
