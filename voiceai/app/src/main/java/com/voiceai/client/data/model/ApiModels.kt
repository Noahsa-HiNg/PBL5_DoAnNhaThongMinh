package com.voiceai.client.data.model

import com.google.gson.annotations.SerializedName

// ── Điều khiển đèn ──────────────────────────────────────
data class LightCommand(
    val state: String  // "on" hoặc "off"
)

// ── Điều khiển cửa ──────────────────────────────────────
data class DoorCommand(
    val action: String  // "lock" hoặc "unlock"
)

// ── Điều khiển quạt ─────────────────────────────────────
data class FanCommand(
    val state: String = "on",
    val speed: Int      // 0 = tắt, 1/2/3 = tốc độ
)

// ── Chế độ tự động ──────────────────────────────────────
data class AutoCommand(
    val command: String  // "ON" hoặc "OFF"
)

// ── Đặt hẹn giờ tuyệt đối ────────────────────────────
data class ScheduleSetRequest(
    val device_name: String,
    val command: String,    // "ON" | "OFF"
    val time: String        // "YYYY-MM-DD HH:mm:ss"
)

// ── Hẹn giờ sau N phút (set-timer) ──────────────────────
data class TimerSetRequest(
    val device_name: String,
    val command: String,
    @SerializedName("delay_minutes")
    val delayMinutes: Int
)

// ── Hẹn giờ hàng loạt (batch) ───────────────────────────
data class BatchScheduleRequest(
    @SerializedName("device_type")
    val deviceType: String,    // "light" | "fan" | "all"
    val command: String,        // "ON" | "OFF"
    @SerializedName("delay_minutes")
    val delayMinutes: Int
)

// ── Response danh sách thiết bị cho hẹn giờ ─────────────
data class ScheduleDevicesResponse(
    val status: String,
    val data: ScheduleDevicesData
)

data class ScheduleDevicesData(
    val devices: List<ScheduleDevice>
)

data class ScheduleDevice(
    @SerializedName("device_id") val deviceId: Int,
    @SerializedName("device_name") val deviceName: String,
    @SerializedName("device_type") val deviceType: String
)

// ── Response danh sách hẹn giờ đang chờ ──────────────────
data class SchedulesResponse(
    val status: String,
    val data: SchedulesData
)

data class SchedulesData(
    val total: Int,
    val schedules: List<Schedule>
)

data class Schedule(
    @SerializedName("schedule_id") val id: Int,
    @SerializedName("device_id") val deviceId: Int,
    @SerializedName("device_name") val deviceName: String,
    val command: String,
    @SerializedName("trigger_time") val triggerTime: String,
    val status: String,
    @SerializedName("created_at") val createdAt: String
)

// ── Response thời tiết ───────────────────────────────────
data class WeatherResponse(
    val status: String,
    val data: WeatherData? = null
)

data class WeatherData(
    val city: String,
    val temperature: Double,
    val humidity: Int,
    val description: String,
    @SerializedName("icon_url")
    val iconUrl: String
)

// ── Response chung dạng message ─────────────────────────
data class MessageResponse(
    val message: String,
    val status: String? = null,
    val detail: String? = null
)

// ── Response danh sách thiết bị ─────────────────────────
data class DevicesResponse(
    val status: String,
    val data: DevicesListData
)

data class DevicesListData(
    val devices: List<Device>
)

// ── Response cảm biến ────────────────────────────────────
data class SensorResponse(
    val status: String,
    val data: SensorData
)

data class SensorData(
    @SerializedName("sensor_id")
    val sensorId: Int,
    val name: String,
    val value1: Double?,    // Nhiệt độ hoặc ánh sáng
    val value2: Double?,    // Độ ẩm (nếu là DHT11)
    val unit1: String? = null,
    val unit2: String? = null,
    val timestamp: String
)

// ── Voice / Chat API Models (PORT 5000) ──────────────────
data class VoiceMessageRequest(
    val message: String
)

data class VoiceMessageResponse(
    val reply: String,
    val transcript: String
)

data class ConversationItem(
    val id: Int,
    val sender: String, // "user" hoặc "system"
    val message: String,
    val timestamp: String
)

data class ConversationHistoryResponse(
    val status: String,
    val data: List<ConversationItem>
)
