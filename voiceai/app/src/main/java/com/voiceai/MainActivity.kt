package com.voiceai

import android.Manifest
import android.content.pm.PackageManager
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import com.voiceai.client.data.preferences.UserPreferences
import com.voiceai.client.ui.dashboard.SensorDashboardViewModel
import com.voiceai.client.ui.main.MainScreen
import com.voiceai.client.ui.theme.VoiceAITheme
import org.koin.android.ext.android.inject
import org.koin.androidx.compose.koinViewModel

class MainActivity : ComponentActivity() {
    private val userPreferences: UserPreferences by inject()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
        // Xin quyền ghi âm lúc Runtime (Bắt buộc cho Android 6.0+)
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.RECORD_AUDIO) 
            != PackageManager.PERMISSION_GRANTED) {
            ActivityCompat.requestPermissions(this, arrayOf(Manifest.permission.RECORD_AUDIO), 0)
        }

        enableEdgeToEdge()
        setContent {
            val themeMode by userPreferences.themeModeFlow.collectAsState()
            
            // SensorViewModel chỉ dùng để lấy currentLight cho chế độ Auto
            val sensorViewModel: SensorDashboardViewModel = koinViewModel()
            val currentLight by sensorViewModel.currentLight.collectAsState()

            val isDarkTheme = when (themeMode) {
                "light" -> false
                "dark" -> true
                else -> { // auto
                    val lightLevel = currentLight ?: 1000.0
                    lightLevel < 1000.0
                }
            }

            VoiceAITheme(darkTheme = isDarkTheme) {
                MainScreen()
            }
        }
    }
}
