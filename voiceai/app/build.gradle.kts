plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.kotlin.compose)
}

android {
    namespace = "com.voiceai"
    compileSdk {
        version = release(36) {
            minorApiLevel = 1
        }
    }

    defaultConfig {
        applicationId = "com.voiceai_dev"
        minSdk = 26
        targetSdk = 36
        versionCode = 1
        versionName = "1.0"

        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
        }
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_11
        targetCompatibility = JavaVersion.VERSION_11
    }
    buildFeatures {
        compose = true
    }
    buildToolsVersion = "36.1.0"
}

dependencies {
    implementation(libs.androidx.core.ktx)
    implementation(libs.androidx.lifecycle.runtime.ktx)
    implementation(libs.androidx.activity.compose)
    implementation(platform(libs.androidx.compose.bom))
    implementation(libs.androidx.compose.ui)
    implementation(libs.androidx.compose.ui.graphics)
    implementation(libs.androidx.compose.ui.tooling.preview)
    implementation(libs.androidx.compose.material3)
    testImplementation(libs.junit)
    androidTestImplementation(libs.androidx.junit)
    androidTestImplementation(libs.androidx.espresso.core)
    androidTestImplementation(platform(libs.androidx.compose.bom))
    androidTestImplementation(libs.androidx.compose.ui.test.junit4)
    debugImplementation(libs.androidx.compose.ui.tooling)
    debugImplementation(libs.androidx.compose.ui.test.manifest)
    // ===== Jetpack Compose BOM =====
    // BOM đảm bảo tất cả Compose libraries dùng cùng version — không bao giờ conflict
    // ===== Socket.IO Client =====
    // Quan trọng: dùng version hỗ trợ binary emit (ByteArray)
    // Loại trừ okhttp để tránh conflict với version khác trong project
    implementation("io.socket:socket.io-client:2.1.0") {
        exclude(group = "org.json", module = "json") // Android đã có built-in
    }

    implementation("androidx.compose.material:material-icons-extended")

    // 2. Thêm Koin cho Compose (Sửa lỗi koinViewModel)
    implementation("io.insert-koin:koin-android:4.0.0")
    implementation("io.insert-koin:koin-androidx-compose:4.0.0")

    // 3. Thêm Lifecycle Compose (Sửa lỗi collectAsStateWithLifecycle)
    implementation("androidx.lifecycle:lifecycle-runtime-compose:2.8.2")

    // 4. Thêm ViewModel cho Compose
    implementation("androidx.lifecycle:lifecycle-viewmodel-compose:2.8.2")
    // ===== Coroutines =====
    implementation("androidx.navigation:navigation-compose:2.7.7")
    implementation("com.squareup.retrofit2:retrofit:2.9.0")
    implementation("com.squareup.retrofit2:converter-gson:2.9.0")
    implementation("com.squareup.okhttp3:logging-interceptor:4.12.0")
    // Debug

}