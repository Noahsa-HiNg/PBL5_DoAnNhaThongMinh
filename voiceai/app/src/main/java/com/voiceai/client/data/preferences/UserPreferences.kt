package com.voiceai.client.data.preferences

import android.content.Context
import androidx.core.content.edit

class UserPreferences(context: Context) {
    private val prefs = context.getSharedPreferences("voiceai_prefs", Context.MODE_PRIVATE)

    companion object {
        private const val KEY_SERVER_IP = "server_ip"
        private const val KEY_SERVER_PORT = "server_port"
    }

    var serverPort: Int
        get() = prefs.getInt(KEY_SERVER_PORT, 5000)
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