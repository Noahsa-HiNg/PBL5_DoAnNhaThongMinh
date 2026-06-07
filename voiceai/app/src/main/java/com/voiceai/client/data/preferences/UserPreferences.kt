package com.voiceai.client.data.preferences

import android.content.Context
import androidx.core.content.edit
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow

class UserPreferences(context: Context) {
    private val prefs = context.getSharedPreferences("voiceai_prefs", Context.MODE_PRIVATE)

    private val _themeModeFlow = MutableStateFlow(prefs.getString(KEY_THEME_MODE, "auto") ?: "auto")
    val themeModeFlow: StateFlow<String> = _themeModeFlow.asStateFlow()

    companion object {
        private const val KEY_SERVER_IP = "server_ip"
        private const val KEY_SERVER_PORT = "server_port"
        private const val KEY_TTS_ENABLED = "tts_enabled"
        private const val KEY_THEME_MODE = "theme_mode" // "light", "dark", "auto"
        const val DEFAULT_MAIN_DOOR_ID = 11
    }

    var themeMode: String
        get() = prefs.getString(KEY_THEME_MODE, "auto") ?: "auto"
        set(value) {
            prefs.edit { putString(KEY_THEME_MODE, value) }
            _themeModeFlow.value = value
        }

    var ttsEnabled: Boolean
        get() = prefs.getBoolean(KEY_TTS_ENABLED, false)
        set(value) {
            prefs.edit { putBoolean(KEY_TTS_ENABLED, value) }
        }

    var serverPort: Int
        get() = prefs.getInt(KEY_SERVER_PORT, 8000)
        set(value) {
            prefs.edit { putInt(KEY_SERVER_PORT, value) }
        }

    var serverIp: String
        get() = prefs.getString(KEY_SERVER_IP, "") ?: ""
        set(value) {
            val trimmed = value.trim()
                .removePrefix("http://")
                .removePrefix("https://")
                .removePrefix("ws://")
                .removePrefix("wss://")
            
            // Nếu người dùng nhập dạng 192.168.1.5:8000
            if (trimmed.contains(":")) {
                val parts = trimmed.split(":")
                val ip = parts[0].trim()
                val portStr = parts[1].trim()
                
                prefs.edit { putString(KEY_SERVER_IP, ip) }
                portStr.toIntOrNull()?.let { serverPort = it }
            } else {
                prefs.edit { putString(KEY_SERVER_IP, trimmed) }
            }
        }

    val serverUrl: String get() = "http://$serverIp:$serverPort"

    fun isConfigured(): Boolean = serverIp.isNotBlank()
}