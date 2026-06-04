package com.voiceai.client.data.model

/**
 * Map với response của GET /api/schedules/active
 * Đây là schedule gắn với device cụ thể, không phải alarm có label
 */
data class Schedule(
    val schedule_id: Int,
    val device_id: Int,
    val command: String,        // "ON", "OFF", hoặc JSON speed cho quạt
    val trigger_time: String,   // "YYYY-MM-DD HH:mm:ss"
    val status: String          // "PENDING" | "DONE" | "CANCELLED"
)