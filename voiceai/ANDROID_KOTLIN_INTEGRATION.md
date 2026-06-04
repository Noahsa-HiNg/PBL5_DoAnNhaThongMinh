# 📱 ANDROID APP API SPECIFICATION — Complete Integration Guide

**Phiên bản:** 2.0  
**Ngày cập nhật:** 2026-05-04  
**Trạng thái:** Ready for Development  
**Công nghệ:** Kotlin + Retrofit + OkHttp  

---

## 🎯 EXECUTIVE SUMMARY

### 3 Chức Năng Chính Của App
1. **💬 Hộp Chat** — Gửi text/ghi âm → AI xử lý → response
2. **🎮 Điều Khiển Nút** — Bật/tắt thiết bị manual
3. **📊 Hiển Thị Trạng Thái** — Xem trạng thái real-time

### Server Info
- **Type:** FastAPI REST API
- **Base URL:** `http://{SERVER_IP}:5000`
- **Authentication:** None (LAN-only, IP whitelist recommended)
- **CORS:** Allows all origins
- **Status Codes:** 200, 201, 400, 404, 500

### Devices Count
- **Total:** 12 devices
- **Types:** Lights (4), Fans (4), Door (1), Buzzer (1), Sensors (2)

---

## 📋 DANH SÁCH THIẾT BỊ CHUẨN

**Tất cả 12 thiết bị có ID cố định - Hardcode vào app:**

| ID | Name | Room | Type | Values | API Control |
|----|------|------|------|--------|-------------|
| 1 | Đèn Phòng Khách | living_room | light | "on"/"off" | ✅ |
| 2 | Đèn Phòng Ngủ | bedroom | light | "on"/"off" | ✅ |
| 3 | Đèn Phòng Bếp | kitchen | light | "on"/"off" | ✅ |
| 4 | Đèn Sân Vườn | yard | light | "on"/"off" | ✅ |
| 5 | Quạt Phòng Khách | living_room | fan | "0"/"1"/"2"/"3" | ✅ |
| 6 | Quạt Phòng Ngủ | bedroom | fan | "0"/"1"/"2"/"3" | ✅ |
| 7 | Quạt Phòng Bếp | kitchen | fan | "0"/"1"/"2"/"3" | ✅ |
| 8 | Quạt Thông Gió Bếp | kitchen | fan | "on"/"off" | ✅ |
| 9 | Cảm Biến Nhiệt-Ẩm | living_room | sensor | "28.5 - 65%" | 📖 (read-only) |
| 10 | Cảm Biến Ánh Sáng | yard | sensor | "0-4095" lux | 📖 (read-only) |
| 11 | Cửa Chính | living_room | door | "locked"/"unlocked" | ⚠️ (partial) |
| 12 | Loa Buzzer | bedroom | buzzer | "on"/"off" | ⚠️ (partial) |

**Legend:** ✅ = Fully working, 📖 = Read-only, ⚠️ = Needs completion

---

## 🚀 ALL API ENDPOINTS

### Group 1: SYSTEM (Hệ Thống)

#### 1.1 Health Check
```
GET /
Response 200: {"message": "✅ PBL5 Smart Home Server v2.0 đang hoạt động!"}
```
**Dùng:** Kiểm tra server có sống không

#### 1.2 Current Time
```
GET /api/time
Response 200: {
  "current_time": "2026-05-04 14:30:45",
  "time_context": "afternoon"
}
```
**time_context:** "morning" (5-12h), "afternoon" (12-17h), "evening" (17-21h), "night" (21-5h)

---

### Group 2: DEVICE CONTROL (Điều Khiển Thiết Bị)

#### 2.1 Light Control — Single
```
POST /api/control/light/{device_id}
Content-Type: application/json

Request body:
{
  "state": "on"   // or "off"
}

Response 200:
{
  "status": "success",
  "message": "Đã gửi lệnh on tới Đèn Phòng Khách",
  "data": {
    "device_id": 1,
    "name": "Đèn Phòng Khách",
    "state": "on",
    "timestamp": "2026-05-04T14:30:45"
  }
}

Response 400:
{
  "status": "error",
  "detail": "Lệnh đèn chỉ được là ON hoặc OFF"
}
```

**device_id:** 1, 2, 3, 4  
**state:** "on" hoặc "off" (case-insensitive)

#### 2.2 Light Control — All
```
POST /api/control/light/all
Body: {"state": "off"}

Response 200:
{
  "status": "success",
  "message": "Đã tắt tất cả đèn",
  "data": {
    "affected_devices": 4,
    "timestamp": "2026-05-04T14:30:45"
  }
}
```

#### 2.3 Fan Control — Speed
```
POST /api/control/fan/{device_id}
Body: {
  "state": "on",
  "speed": 2
}

Response 200:
{
  "status": "success",
  "message": "Đã gửi lệnh cho Quạt 5",
  "data": {
    "device_id": 5,
    "speed": 2,
    "timestamp": "2026-05-04T14:30:45"
  }
}
```

**device_id:** 5, 6, 7, 8  
**speed:** 0 (off), 1 (slow), 2 (medium), 3 (fast)  
**state:** "on" = bật ở speed đó, "off" = speed 0

#### 2.4 Fan Control — Adjust
```
POST /api/control/fan/{device_id}/adjust
Body: {"action": "up"}  // or "down"

Response 200:
{
  "status": "success",
  "message": "Đã tăng tốc Quạt 5 lên mức 3",
  "data": {
    "device_id": 5,
    "new_speed": 3,
    "timestamp": "2026-05-04T14:30:45"
  }
}
```

#### 2.5 Door Control ⚠️
```
POST /api/control/door
Body: {"action": "lock"}  // or "unlock"

Response 200: (may vary - needs verification)
```

#### 2.6 Buzzer Control ⚠️
```
POST /api/control/buzzer
Body: {"state": "on"}  // "on", "off", or "beep"

Response 200: (needs verification)
```

---

### Group 3: DEVICE STATUS (Lấy Trạng Thái)

#### 3.1 All Devices
```
GET /api/status/devices

Response 200:
{
  "status": "success",
  "data": {
    "devices": [
      {
        "device_id": 1,
        "room_id": 1,
        "name": "Đèn Phòng Khách",
        "type": "light",
        "pin": 18,
        "state": "off"
      },
      {
        "device_id": 5,
        "room_id": 1,
        "name": "Quạt Phòng Khách",
        "type": "fan",
        "pin": 26,
        "state": "2"
      },
      // ... 10 devices more
    ]
  }
}
```

#### 3.2 Single Device
```
GET /api/status/devices/{device_id}

Response 200:
{
  "status": "success",
  "data": {
    "device_id": 1,
    "name": "Đèn Phòng Khách",
    "type": "light",
    "state": "off"
  }
}

Response 404:
{
  "status": "error",
  "detail": "Không tìm thấy thiết bị"
}
```

#### 3.3 All Devices in Room
```
GET /api/status/rooms/{room_slug}

Possible slugs: "living_room", "bedroom", "kitchen", "yard"

Response 200:
{
  "status": "success",
  "data": {
    "room": "Phòng Khách",
    "slug": "living_room",
    "devices": [
      {"device_id": 1, "name": "Đèn Phòng Khách", "type": "light", "state": "off"},
      {"device_id": 5, "name": "Quạt Phòng Khách", "type": "fan", "state": "2"},
      // ... devices in room
    ]
  }
}
```

#### 3.4 Door Status
```
GET /api/status/door

Response 200:
{
  "status": "success",
  "data": {
    "device_id": 11,
    "name": "Cửa Chính",
    "state": "locked"
  }
}
```

---

### Group 4: SENSORS (Cảm Biến)

#### 4.1 Latest Sensor Reading
```
GET /api/sensors/{sensor_id}

sensor_id: 9 (temp+humidity) or 10 (light)

Response 200:
{
  "status": "success",
  "data": {
    "sensor_id": 9,
    "name": "Cảm biến Nhiệt-Ẩm",
    "value1": 28.5,         // temp in °C
    "value2": 65,           // humidity %
    "unit1": "°C",
    "unit2": "%",
    "timestamp": "2026-05-04T14:30:45"
  }
}
```

#### 4.2 All Sensors
```
GET /api/sensors

Response 200:
{
  "status": "success",
  "data": {
    "sensors": [
      {"sensor_id": 9, "name": "Temp+Humidity", ...},
      {"sensor_id": 10, "name": "Light", ...}
    ]
  }
}
```

#### 4.3 Sensor History (Last 10 readings)
```
GET /api/sensors/history/{sensor_id}?limit=10&offset=0

Response 200:
{
  "status": "success",
  "data": {
    "readings": [
      {"timestamp": "...", "value1": 28.5, "value2": 65},
      // ... 9 more readings
    ]
  }
}
```

---

### Group 5: SCHEDULES & ALARMS (Hẹn Giờ & Báo Thức)

#### 5.1 Set Schedule (Absolute Time)
```
POST /api/schedules/set
Body: {
  "device_id": 1,
  "command": "ON",
  "time": "2026-05-04 07:30:00"
}

Response 201:
{
  "status": "success",
  "message": "Đã đặt hẹn giờ cho Đèn Phòng Khách vào lúc 07:30",
  "data": {
    "schedule_id": 1,
    "trigger_time": "2026-05-04 07:30:00",
    "status": "PENDING"
  }
}
```

#### 5.2 Set Timer (Relative Time)
```
POST /api/schedules/set-timer
Body: {
  "device_id": 5,
  "command": "OFF",
  "delay_minutes": 30
}

Response 201:
{
  "status": "success",
  "message": "Đã hẹn giờ tắt Quạt 5 sau 30 phút"
}
```

#### 5.3 Set Batch Timer
```
POST /api/schedules/batch
Body: {
  "device_type": "light",  // or "fan" or "all"
  "command": "OFF",
  "delay_minutes": 60
}

Response 201: Hẹn giờ tất cả thiết bị loại đó
```

#### 5.4 List Active Schedules
```
GET /api/schedules/active

Response 200:
{
  "status": "success",
  "data": {
    "active_schedules": [
      {
        "schedule_id": 1,
        "device_id": 1,
        "command": "ON",
        "trigger_time": "2026-05-04 07:30:00",
        "status": "PENDING",
        "type": "absolute"
      }
    ],
    "count": 1
  }
}
```

#### 5.5 Cancel Schedule
```
DELETE /api/schedules/{schedule_id}

Response 200:
{
  "status": "success",
  "message": "Đã hủy hẹn giờ #1"
}
```

#### 5.6 Set Alarm (Daily)
```
POST /api/alarms/set
Body: {
  "time": "07:30",
  "repeat": true,
  "label": "Báo thức buổi sáng"
}

Response 201:
{
  "status": "success",
  "message": "Đã đặt báo thức lúc 07:30",
  "data": {
    "alarm_id": 1,
    "time": "07:30",
    "repeat": true,
    "label": "Báo thức buổi sáng"
  }
}
```

#### 5.7 List Alarms
```
GET /api/alarms

Response 200:
{
  "status": "success",
  "data": {
    "alarms": [
      {"alarm_id": 1, "time": "07:30", "repeat": true, "label": "..."}
    ]
  }
}
```

#### 5.8 Delete Alarm
```
DELETE /api/alarms/{alarm_id}

Response 200:
{
  "status": "success",
  "message": "Đã xóa báo thức #1"
}
```

---

### Group 6: BULK OPERATIONS (Điều Khiển Hàng Loạt)

#### 6.1 Bulk Control Multiple
```
POST /api/bulk/control
Body: {
  "actions": [
    {"device_id": 1, "command": "ON"},
    {"device_id": 5, "command": "OFF"}
  ]
}

Response 200:
{
  "status": "success",
  "message": "Đã thực thi 2 lệnh",
  "data": {
    "executed": 2,
    "failed": 0
  }
}
```

#### 6.2 Control All
```
POST /api/bulk/all
Body: {"state": "OFF"}

Response 200:
{
  "status": "success",
  "message": "Đã tắt tất cả thiết bị"
}
```

---

### Group 7: WEATHER (Thời Tiết)

#### 7.1 Weather Current
```
GET /api/weather/current?city=Da%20Nang

Response 200:
{
  "status": "success",
  "data": {
    "city": "Da Nang",
    "temperature": 32.5,
    "humidity": 75,
    "description": "Trời nắng",
    "icon_url": "http://openweathermap.org/img/wn/01d@2x.png"
  }
}

Response 404:
{
  "status": "error",
  "detail": "Không tìm thấy dữ liệu thời tiết cho khu vực"
}
```

---

### Group 8: CONTEXT SUGGESTIONS (Gợi Ý Thủ Công)

#### 8.1 Get Suggestions
```
GET /api/context/suggestions

Response 200:
{
  "status": "success",
  "data": {
    "context": "hot",
    "reason": "Nhiệt độ phòng đang 31°C, cao hơn ngưỡng thoải mái",
    "suggestions": [
      {
        "pending_id": "pending_001",
        "device_id": 5,
        "device_name": "Quạt Phòng Khách",
        "action": "ON",
        "detail": "Bật quạt tốc độ 3"
      }
    ],
    "expires_in": 60
  }
}
```

#### 8.2 Confirm Suggestion
```
POST /api/context/confirm
Body: {
  "pending_id": "pending_001",
  "confirm": true  // or false to reject
}

Response 200:
{
  "status": "success",
  "message": "Đã thực thi gợi ý",
  "data": {
    "executed": true
  }
}
```

---



## 🛠️ KOTLIN SETUP & CODE EXAMPLES

### Step 1: Dependencies (build.gradle.kts)
```kotlin
dependencies {
    // Retrofit + OkHttp
    implementation("com.squareup.retrofit2:retrofit:2.9.0")
    implementation("com.squareup.retrofit2:converter-gson:2.9.0")
    implementation("com.squareup.okhttp3:okhttp:4.11.0")
    implementation("com.squareup.okhttp3:logging-interceptor:4.11.0")
    
    // Coroutines
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.7.1")
    
    // Jetpack
    implementation("androidx.lifecycle:lifecycle-viewmodel-ktx:2.6.1")
    implementation("androidx.lifecycle:lifecycle-runtime-ktx:2.6.1")
}
```

### Step 2: Data Models
```kotlin
// Common response wrapper
data class ApiResponse(
    val status: String,
    val message: String? = null,
    val data: Any? = null,
    val detail: String? = null
)

// Device model
data class Device(
    val device_id: Int,
    val room_id: Int,
    val name: String,
    val type: String,
    val pin: Int,
    val state: String,
    val timestamp: String? = null
)

// Device list response
data class DevicesResponse(
    val status: String,
    val data: DevicesList
)

data class DevicesList(
    val devices: List<Device>
)

// Chat responses
data class ChatResponse(
    val status: String,
    val reply: String,
    val transcript: String?,
    val intent: String,
    val confidence: Float?,
    val actions_taken: List<ActionTaken>,
    val timestamp: String
)

data class ActionTaken(
    val device_key: String,
    val device_id: Int,
    val action: String
)
```

### Step 3: Retrofit Service Interface
```kotlin
interface SmartHomeApi {
    // System
    @GET("/")
    suspend fun healthCheck(): ApiResponse
    
    @GET("/api/time")
    suspend fun getCurrentTime(): Any
    
    // Device Status
    @GET("/api/status/devices")
    suspend fun getAllDevices(): DevicesResponse
    
    @GET("/api/status/devices/{id}")
    suspend fun getDevice(@Path("id") deviceId: Int): Any
    
    @GET("/api/status/rooms/{slug}")
    suspend fun getRoomDevices(@Path("slug") roomSlug: String): Any
    
    @GET("/api/status/door")
    suspend fun getDoorStatus(): Any
    
    // Device Control - Lights
    @POST("/api/control/light/{id}")
    suspend fun controlLight(
        @Path("id") deviceId: Int,
        @Body body: Map<String, String>
    ): Any
    
    @POST("/api/control/light/all")
    suspend fun controlAllLights(
        @Body body: Map<String, String>
    ): Any
    
    // Device Control - Fans
    @POST("/api/control/fan/{id}")
    suspend fun controlFan(
        @Path("id") deviceId: Int,
        @Body body: Map<String, Any>
    ): Any
    
    @POST("/api/control/fan/{id}/adjust")
    suspend fun adjustFanSpeed(
        @Path("id") deviceId: Int,
        @Body body: Map<String, String>
    ): Any
    
    // Device Control - Door/Buzzer
    @POST("/api/control/door")
    suspend fun controlDoor(@Body body: Map<String, String>): Any
    
    @POST("/api/control/buzzer")
    suspend fun controlBuzzer(@Body body: Map<String, String>): Any
    
    // Sensors
    @GET("/api/sensors/{id}")
    suspend fun getSensor(@Path("id") sensorId: Int): Any
    
    @GET("/api/sensors")
    suspend fun getAllSensors(): Any
    
    // Schedules
    @POST("/api/schedules/set")
    suspend fun setSchedule(@Body body: Any): Any
    
    @POST("/api/schedules/set-timer")
    suspend fun setTimer(@Body body: Any): Any
    
    @GET("/api/schedules/active")
    suspend fun getActiveSchedules(): Any
    
    @DELETE("/api/schedules/{id}")
    suspend fun cancelSchedule(@Path("id") scheduleId: Int): Any
    
    // Alarms
    @POST("/api/alarms/set")
    suspend fun setAlarm(@Body body: Any): Any
    
    @GET("/api/alarms")
    suspend fun getAlarms(): Any
    
    @DELETE("/api/alarms/{id}")
    suspend fun deleteAlarm(@Path("id") alarmId: Int): Any
    
    // Bulk
    @POST("/api/bulk/control")
    suspend fun bulkControl(@Body body: Any): Any
    
    @POST("/api/bulk/all")
    suspend fun controlAll(@Body body: Map<String, String>): Any
    
    // Weather
    @GET("/api/weather/current")
    suspend fun getWeather(@Query("city") city: String): Any
    
    // Context
    @GET("/api/context/suggestions")
    suspend fun getSuggestions(): Any
    
    @POST("/api/context/confirm")
    suspend fun confirmSuggestion(@Body body: Map<String, Any>): Any
    
    // Chat (TBD)
    @POST("/api/chat/message")
    suspend fun chatMessage(@Body body: Map<String, String>): ChatResponse
    
    @Multipart
    @POST("/api/chat/audio")
    suspend fun chatAudio(@Part file: MultipartBody.Part): ChatResponse
}
```

### Step 4: Retrofit Client Setup
```kotlin
object RetrofitClient {
    private const val DEFAULT_URL = "http://192.168.1.100:5000/"
    private var baseUrl = DEFAULT_URL
    
    fun setBaseUrl(ip: String) {
        baseUrl = "http://$ip:5000/"
    }
    
    private fun getOkHttpClient(): OkHttpClient {
        val logging = HttpLoggingInterceptor().apply {
            level = HttpLoggingInterceptor.Level.BODY
        }
        
        return OkHttpClient.Builder()
            .addInterceptor(logging)
            .connectTimeout(5, TimeUnit.SECONDS)
            .readTimeout(30, TimeUnit.SECONDS)
            .writeTimeout(30, TimeUnit.SECONDS)
            .build()
    }
    
    fun getApi(): SmartHomeApi {
        return Retrofit.Builder()
            .baseUrl(baseUrl)
            .client(getOkHttpClient())
            .addConverterFactory(GsonConverterFactory.create())
            .build()
            .create(SmartHomeApi::class.java)
    }
}
```

### Step 5: Example - ViewModel for Lights
```kotlin
class LightViewModel : ViewModel() {
    private val api = RetrofitClient.getApi()
    
    private val _devices = MutableStateFlow<List<Device>>(emptyList())
    val devices: StateFlow<List<Device>> = _devices.asStateFlow()
    
    private val _isLoading = MutableStateFlow(false)
    val isLoading: StateFlow<Boolean> = _isLoading.asStateFlow()
    
    private val _error = MutableStateFlow<String?>(null)
    val error: StateFlow<String?> = _error.asStateFlow()
    
    fun loadDevices() {
        viewModelScope.launch {
            _isLoading.value = true
            try {
                val response = api.getAllDevices()
                _devices.value = response.data.devices
                _error.value = null
            } catch (e: Exception) {
                _error.value = e.message ?: "Unknown error"
            } finally {
                _isLoading.value = false
            }
        }
    }
    
    fun toggleLight(deviceId: Int) {
        viewModelScope.launch {
            try {
                val currentDevice = _devices.value.find { it.device_id == deviceId }
                val newState = if (currentDevice?.state == "on") "off" else "on"
                
                api.controlLight(deviceId, mapOf("state" to newState))
                
                // Update local state
                _devices.value = _devices.value.map {
                    if (it.device_id == deviceId) it.copy(state = newState) else it
                }
            } catch (e: Exception) {
                _error.value = e.message ?: "Control failed"
            }
        }
    }
}
```

---

## ⚠️ ERROR HANDLING

### Common HTTP Errors

| Code | Meaning | Handle |
|------|---------|--------|
| 200 | Success | Parse response |
| 201 | Created | Confirm success |
| 400 | Bad Request | Show: "Lệnh không hợp lệ" |
| 404 | Not Found | Show: "Không tìm thấy thiết bị" |
| 500 | Server Error | Show: "Lỗi server, thử lại" |

### Network Errors

```kotlin
try {
    // API call
} catch (e: SocketTimeoutException) {
    // Timeout after 30s
    showError("Timeout - Server không phản hồi")
} catch (e: ConnectException) {
    // Connection failed
    showError("Không kết nối được server")
} catch (e: HttpException) {
    // HTTP error
    when (e.code()) {
        400 -> showError("Yêu cầu sai: ${e.message()}")
        404 -> showError("Thiết bị không tồn tại")
        500 -> showError("Lỗi server")
        else -> showError("Lỗi ${e.code()}")
    }
} catch (e: IOException) {
    // Network error
    showError("Lỗi mạng - Kiểm tra WiFi")
} catch (e: Exception) {
    // Other
    showError("Lỗi: ${e.message}")
}
```

---

## 📱 HARDCODED VALUES FOR APP

### Device IDs (Use These in Spinner/Buttons)
```kotlin
val deviceMap = mapOf(
    1 to "Đèn Phòng Khách",
    2 to "Đèn Phòng Ngủ",
    3 to "Đèn Phòng Bếp",
    4 to "Đèn Sân Vườn",
    5 to "Quạt Phòng Khách",
    6 to "Quạt Phòng Ngủ",
    7 to "Quạt Phòng Bếp",
    8 to "Quạt Thông Gió",
    11 to "Cửa Chính",
    12 to "Loa Buzzer"
)

val sensorMap = mapOf(
    9 to "Cảm biến Nhiệt-Ẩm",
    10 to "Cảm biến Ánh Sáng"
)

val roomMap = mapOf(
    "living_room" to "Phòng Khách",
    "bedroom" to "Phòng Ngủ",
    "kitchen" to "Nhà Bếp",
    "yard" to "Sân Vườn"
)
```

### Fan Speed Labels
```kotlin
val fanSpeedMap = mapOf(
    "0" to "Tắt",
    "1" to "Chậm",
    "2" to "Trung bình",
    "3" to "Nhanh"
)
```

---

## 🔐 SECURITY NOTES

⚠️ **Current State:** NO AUTHENTICATION
- Server accepts all IP addresses (CORS: "*")
- Designed for LAN-only use
- Store server IP in SharedPreferences (not hardcoded)

### Minimum Security (Recommended Before Deploy)
```kotlin
// In SharedPreferences
fun saveServerIP(context: Context, ip: String) {
    context.getSharedPreferences("config", Context.MODE_PRIVATE)
        .edit()
        .putString("server_ip", ip)
        .apply()
}

fun getServerIP(context: Context): String {
    return context.getSharedPreferences("config", Context.MODE_PRIVATE)
        .getString("server_ip", "192.168.1.100") ?: "192.168.1.100"
}
```

---

## 🎯 IMPLEMENTATION CHECKLIST

### Phase 1: Basic Setup
- [ ] Add dependencies (Retrofit, OkHttp, Gson)
- [ ] Create data models
- [ ] Create API service interface
- [ ] Setup Retrofit client
- [ ] Test health check endpoint

### Phase 2: Device Control
- [ ] Load all devices
- [ ] Display devices in UI
- [ ] Implement light toggle
- [ ] Implement fan speed control
- [ ] Display real-time status

### Phase 3: Additional Features
- [ ] Sensor readings (temp, light)
- [ ] Schedules & alarms
- [ ] Weather integration
- [ ] Context suggestions

### Phase 4: Chat (After Backend Implements Endpoints)
- [ ] Setup audio recorder (WAV format)
- [ ] Implement chat text send
- [ ] Implement audio upload
- [ ] Display transcript + response
- [ ] Show device actions

### Phase 5: Polish
- [ ] Error handling & retry logic
- [ ] Loading spinners
- [ ] Success/failure toasts
- [ ] Pull-to-refresh
- [ ] Offline fallback

---

## 📊 DATABASE STRUCTURE (Reference)

**Tables:**
- `rooms` - 4 rooms (living_room, bedroom, kitchen, yard)
- `devices` - 12 devices (hardcoded IDs)
- `device_history` - sensor readings (timestamp, values)
- `schedules` - pending/completed jobs
- `alarms` - daily alarms with repeat flag

**All device IDs are fixed - no need to fetch from DB**

---

## 🧪 QUICK TEST (cURL Commands)

```bash
# 1. Health check
curl http://192.168.1.100:5000/

# 2. Get all devices
curl http://192.168.1.100:5000/api/status/devices

# 3. Turn on light
curl -X POST http://192.168.1.100:5000/api/control/light/1 \
  -H "Content-Type: application/json" \
  -d '{"state":"on"}'

# 4. Set fan speed
curl -X POST http://192.168.1.100:5000/api/control/fan/5 \
  -H "Content-Type: application/json" \
  -d '{"state":"on","speed":2}'

# 5. Get sensors
curl http://192.168.1.100:5000/api/sensors

# 6. Get weather
curl "http://192.168.1.100:5000/api/weather/current?city=Da%20Nang"
```

---

## 📞 SUPPORT

**API Status:**
- ✅ 28/30 endpoints working
- ⚠️ 2 endpoints need completion (door, buzzer)
- 🆕 2 endpoints not yet implemented (chat text, chat audio)

**For Android Dev:**
1. Use hardcoded device IDs (1-12)
2. Handle timeout (30s) - NLU is slow
3. Always wrap responses in try-catch
4. Fallback device list when API fails
5. Poll device status every 2-5 seconds for real-time UI

---

**Created:** 2026-05-04  
**Target:** Android App (Kotlin)  
**Status:** Ready for Implementation ✅
