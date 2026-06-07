// di/AppModule.kt
package com.voiceai.client.di

import com.voiceai.client.data.network.ApiService
import com.voiceai.client.data.network.DeviceRepository
import com.voiceai.client.data.network.ScheduleRepository
import com.voiceai.client.data.network.SocketRepository
import com.voiceai.client.data.audio.AudioRepository
import com.voiceai.client.data.audio.TtsHelper
import com.voiceai.client.data.notification.NotificationHelper
import com.voiceai.client.data.preferences.UserPreferences
import com.voiceai.client.data.network.ChatRepository
import com.voiceai.client.data.local.AppDatabase
import com.voiceai.client.data.local.LocalDeviceRepository
import androidx.room.Room
import com.voiceai.client.ui.chat.ChatViewModel
import com.voiceai.client.ui.devices.DevicesViewModel
import com.voiceai.client.ui.settings.SettingsViewModel
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import org.koin.androidx.viewmodel.dsl.viewModel
import org.koin.dsl.module
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import java.util.concurrent.TimeUnit

val appModule = module {

    single { UserPreferences(get()) }

    // ✅ FIX: OkHttp với timeout dài hơn + logging + dynamic URL interceptor đúng cách
    single {
        val logging = HttpLoggingInterceptor().apply {
            level = HttpLoggingInterceptor.Level.BASIC
        }
        OkHttpClient.Builder()
            .connectTimeout(15, TimeUnit.SECONDS)   // LAN có thể chậm lúc đầu
            .readTimeout(30, TimeUnit.SECONDS)
            .writeTimeout(30, TimeUnit.SECONDS)
            .addInterceptor(logging)
            .addInterceptor { chain ->
                val prefs: UserPreferences = get()
                val serverIp = prefs.serverIp          // vd: "192.168.1.100"
                val originalRequest = chain.request()

                // Nếu chưa cấu hình IP, cho qua request gốc (sẽ lỗi baseUrl nhưng không crash interceptor)
                if (serverIp.isBlank()) {
                    return@addInterceptor chain.proceed(originalRequest)
                }

                // ✅ FIX: Phải build lại URL hoàn chỉnh với IP và Port thực từ UserPreferences
                val newUrl = try {
                    originalRequest.url.newBuilder()
                        .host(serverIp)
                        .port(prefs.serverPort)
                        .scheme("http")
                        .build()
                } catch (e: Exception) {
                    originalRequest.url
                }

                val newRequest = originalRequest.newBuilder()
                    .url(newUrl)
                    .build()
                chain.proceed(newRequest)
            }
            .build()
    }

    // ✅ FIX: Base URL dùng placeholder — interceptor sẽ thay thế host và port thực
    single {
        Retrofit.Builder()
            .baseUrl("http://localhost/")  // placeholder, interceptor override
            .client(get<OkHttpClient>())
            .addConverterFactory(GsonConverterFactory.create())
            .build()
            .create(ApiService::class.java)
    }

    // ✅ SocketRepository là singleton — KHÔNG tạo mới khi đổi IP
    single { SocketRepository(get()) }

    single { NotificationHelper(get()) }
    single { DeviceRepository(get()) }
    single { ScheduleRepository(get()) }
    single { AudioRepository(get()) }
    single { ChatRepository(get()) }
    single { TtsHelper(get()) }

    // ===== Room Database =====
    single {
        Room.databaseBuilder(get(), AppDatabase::class.java, "voiceai.db")
            .fallbackToDestructiveMigration()
            .build()
    }
    single { get<AppDatabase>().deviceDao() }
    single { get<AppDatabase>().sensorReadingDao() }
    single { get<AppDatabase>().conversationDao() }
    single { get<AppDatabase>().automationRuleDao() }
    single { LocalDeviceRepository(get()) }

    viewModel { ChatViewModel(get(), get(), get(), get(), get()) }
    viewModel { DevicesViewModel(get(), get(), get(), get()) }
    viewModel { com.voiceai.client.ui.alarms.SchedulesViewModel(get(), get()) }
    viewModel { SettingsViewModel(get(), get(), get()) }
    viewModel { com.voiceai.client.ui.dashboard.SensorDashboardViewModel(get(), get(), get()) }
}