// MyApp.kt
package com.voiceai.client

import android.app.Application
import com.voiceai.client.data.network.SocketRepository
import com.voiceai.client.data.preferences.UserPreferences
import com.voiceai.client.di.appModule
import org.koin.android.ext.android.inject
import org.koin.android.ext.koin.androidContext
import org.koin.core.context.startKoin

class MyApp : Application() {

    override fun onCreate() {
        super.onCreate()

        startKoin {
            androidContext(this@MyApp)
            modules(appModule)
        }

        // Lấy dependency thủ công sau khi khởi tạo Koin
        val socketRepository: SocketRepository by inject()
        val prefs: UserPreferences by inject()

        // ✅ Auto-connect nếu đã có IP lưu sẵn
        if (prefs.isConfigured()) {
            socketRepository.connect()
        }
    }
}