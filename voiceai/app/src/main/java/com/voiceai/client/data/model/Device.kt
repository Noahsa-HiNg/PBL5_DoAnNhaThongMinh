package com.voiceai.client.data.model

import com.google.gson.annotations.SerializedName

/**
 * Model thiết bị khớp với API v2.0
 */
data class Device(
    @SerializedName("device_id")
    val id: Int,
    
    @SerializedName("room_id")
    val roomId: Int? = null,
    
    val name: String,
    val type: String,   // "light" | "fan" | "sensor" | "door" | "buzzer"
    val pin: Int? = null,
    
    @SerializedName("state")
    val status: String,  // "on", "off", "0", "1", "2", "3", "locked", "unlocked"
    
    val timestamp: String? = null
) {
    // Helper computed properties để UI dễ dùng
    val isOn: Boolean get() = when (type) {
        "light" -> status.lowercase() == "on"
        "fan"   -> status != "0" && status.lowercase() != "off"
        "door"  -> status.lowercase() == "unlocked"
        "buzzer" -> status.lowercase() == "on"
        else    -> false
    }

    val fanSpeed: Int get() = status.toIntOrNull() ?: 0

    val displayStatus: String get() = when (type) {
        "light" -> if (isOn) "Đang bật" else "Đang tắt"
        "fan"   -> when (fanSpeed) {
            0 -> "Tắt"
            1 -> "Tốc độ 1"
            2 -> "Tốc độ 2"
            3 -> "Tốc độ 3 (Max)"
            else -> "Tắt"
        }
        "door" -> if (isOn) "Mở khóa" else "Đã khóa"
        "sensor" -> status
        else -> status
    }
}
