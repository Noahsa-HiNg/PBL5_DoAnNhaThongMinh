package com.voiceai.client.data.network

import com.voiceai.client.data.model.*
import retrofit2.http.*

interface ApiService {

    // ════════════════════════════════════════════
    //  HỆ THỐNG
    // ════════════════════════════════════════════

    @GET("/")
    suspend fun getRoot(): MessageResponse

    @GET("api/time")
    suspend fun getCurrentTime(): MessageResponse

    // ════════════════════════════════════════════
    //  TRẠNG THÁI THIẾT BỊ
    // ════════════════════════════════════════════

    /** GET /api/status/devices — lấy toàn bộ thiết bị */
    @GET("api/status/devices")
    suspend fun getAllDevices(): DevicesResponse

    /** GET /api/sensors/{id} — cảm biến mới nhất */
    @GET("api/sensors/{id}")
    suspend fun getSensorStatus(@Path("id") sensorId: Int): SensorResponse

    /** GET /api/status/rooms/{slug} */
    @GET("api/status/rooms/{slug}")
    suspend fun getRoomDevices(@Path("slug") roomSlug: String): DevicesResponse

    // ════════════════════════════════════════════
    //  ĐIỀU KHIỂN THIẾT BỊ
    // ════════════════════════════════════════════

    /** POST /api/control/light/all */
    @POST("api/control/light/all")
    suspend fun controlAllLights(@Body command: LightCommand): MessageResponse

    /**
     * POST /api/control/light/{device_id}
     * body: { "state": "on" | "off" }
     */
    @POST("api/control/light/{device_id}")
    suspend fun controlLight(
        @Path("device_id") deviceId: Int,
        @Body command: LightCommand
    ): MessageResponse

    /**
     * POST /api/control/fan/{device_id}
     * body: { "state": "on", "speed": 0-3 }
     */
    @POST("api/control/fan/{device_id}")
    suspend fun controlFan(
        @Path("device_id") deviceId: Int,
        @Body command: FanCommand
    ): MessageResponse

    /** POST /api/control/fan/{id}/adjust */
    @POST("api/control/fan/{id}/adjust")
    suspend fun adjustFanSpeed(
        @Path("id") deviceId: Int,
        @Body body: Map<String, String>
    ): MessageResponse

    /**
     * POST /api/control/door/{device_id}
     * body: { "action": "lock" | "unlock" }
     */
    @POST("api/control/door/{device_id}")
    suspend fun controlDoor(
        @Path("device_id") deviceId: Int,
        @Body command: DoorCommand
    ): MessageResponse

    /** POST /api/control/buzzer */
    @POST("api/control/buzzer")
    suspend fun controlBuzzer(@Body command: Map<String, String>): MessageResponse

    // ════════════════════════════════════════════
    //  HẸN GIỜ & BÁO THỨC
    // ════════════════════════════════════════════

    /** POST /api/schedules/set */
    @POST("api/schedules/set")
    suspend fun setSchedule(@Body req: AlarmRequest): MessageResponse

    /** POST /api/schedules/set-timer */
    @POST("api/schedules/set-timer")
    suspend fun setTimer(@Body req: TimerRequest): MessageResponse

    /** GET /api/schedules/active */
    @GET("api/schedules/active")
    suspend fun getActiveSchedules(): List<Schedule>

    /** DELETE /api/schedules/{id} */
    @DELETE("api/schedules/{id}")
    suspend fun cancelSchedule(@Path("id") scheduleId: Int): MessageResponse

    /** DELETE /api/schedules/all */
    @DELETE("api/schedules/all")
    suspend fun cancelAllSchedules(): MessageResponse

    // ════════════════════════════════════════════
    //  THỜI TIẾT
    // ════════════════════════════════════════════

    @GET("api/weather/current")
    suspend fun getCurrentWeather(
        @Query("city") city: String = "Da Nang"
    ): WeatherResponse

    // ════════════════════════════════════════════
    //  VOICE / CHAT
    // ════════════════════════════════════════════

    @POST("api/voice/message")
    suspend fun sendVoiceMessage(@Body body: VoiceMessageRequest): VoiceMessageResponse

    @Multipart
    @POST("api/voice/upload")
    suspend fun uploadAudio(
        @Part file: okhttp3.MultipartBody.Part
    ): VoiceMessageResponse

    @GET("api/voice/conversations")
    suspend fun getConversations(@Query("limit") limit: Int = 100): ConversationHistoryResponse

    // ════════════════════════════════════════════
    //  SENSOR HISTORY
    // ════════════════════════════════════════════

    @GET("api/sensors/{id}/history")
    suspend fun getSensorHistory(
        @Path("id") sensorId: Int,
        @Query("limit") limit: Int = 50
    ): SensorHistoryResponse
}

data class SensorHistoryResponse(
    val status: String,
    val data: List<SensorReadingDto>
)

data class SensorReadingDto(
    val value1: Double?,
    val value2: Double?,
    val timestamp: String
)
