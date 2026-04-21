# PBL5 Smart Home — Tài Liệu Kiến Trúc Tổng Thể

> **Mục đích:** Tài liệu này mô tả toàn bộ kiến trúc, luồng dữ liệu, cấu trúc code và các ràng buộc kỹ thuật của dự án. Được viết để AI có thể đọc và hiểu đầy đủ hệ thống mà không cần đọc source code.

---

## 1. Tổng Quan Hệ Thống

### 1.1 Kiến trúc 3 tầng

```
Flutter App  <==HTTP REST (port 8000)==>  FastAPI Backend  <==MQTT (port 1883)==>  ESP32
                                                  |
                                             SQLite DB
                                          (smart_home2.db)
```

### 1.2 Công nghệ sử dụng

| Tầng | Công nghệ | Chi tiết |
|------|-----------|----------|
| Backend | Python 3.11, FastAPI, Uvicorn | REST API server |
| MQTT Broker | Mosquitto | Chạy trên máy tính (cùng mạng WiFi) |
| Database | SQLite 3 | File `smart_home2.db` trong `backend/core/` |
| Hardware | ESP32 (Arduino framework) | WiFi + MQTT client |
| Cảm biến | DHT11 | Nhiệt độ + độ ẩm |
| Cảm biến | LDR/Analog | Đọc ADC 12-bit (0-4095) |
| Cơ cấu chấp hành | Servo Motor | Điều khiển cửa |
| Cơ cấu chấp hành | PWM (analogWrite) | Điều khiển quạt |
| Cơ cấu chấp hành | GPIO Digital | Điều khiển đèn, buzzer |

### 1.3 Địa chỉ mạng (cấu hình hiện tại)

```
MQTT Broker IP : 172.20.10.2
MQTT Port      : 1883
Backend Port   : 8000
WiFi SSID      : hieu
```

---

## 2. Thiết Bị và Phòng

### 2.1 Danh sách phòng (bảng `rooms`)

| id | name | slug |
|----|------|------|
| 1 | Phòng Khách | living_room |
| 2 | Phòng Ngủ | bedroom |
| 3 | Nhà Bếp | kitchen |
| 4 | Sân Vườn | yard |

### 2.2 Danh sách thiết bị (bảng `devices`)

| device_id | room_id | name | type | GPIO Pin | status mặc định |
|-----------|---------|------|------|----------|-----------------|
| 1 | 1 | Đèn Phòng Khách | light | 18 | "off" |
| 2 | 2 | Đèn Phòng Ngủ | light | 19 | "off" |
| 3 | 3 | Đèn Bếp | light | 21 | "off" |
| 4 | 4 | Đèn Sân Vườn | light | 22 | "off" |
| 5 | 1 | Quạt Phòng Khách | fan | 26 | "0" |
| 6 | 2 | Quạt Phòng Ngủ | fan | 25 | "0" |
| 7 | 3 | Quạt Bếp | fan | 33 | "0" |
| 8 | 3 | Quạt Thông Gió | fan | 32 | "0" |
| 9 | 1 | Cảm biến Nhiệt ẩm | sensor | 4 | "0" |
| 10 | 4 | Cảm biến Ánh sáng | light_sensor | 35 | "0" |
| 11 | 1 | Cửa Chính | door_lock | 13 | "locked" |
| 12 | 2 | Loa (Buzzer) | buzzer | 16 | "off" |

**Quy ước giá trị status:**
- Đèn: "on" / "off" (lowercase)
- Quạt: "0", "1", "2", "3" (string của số tốc độ)
- Cửa: "locked" / "unlocked" (lowercase)
- Buzzer: "on" / "off" (lowercase)
- Cảm biến nhiệt ẩm: "28.5 - 65%" (cập nhật từ MQTT)
- Cảm biến ánh sáng: "2500" (giá trị ADC 0-4095 dạng string)

---

## 3. Luồng Dữ Liệu MQTT

### 3.1 Backend gửi xuống ESP32 (Control)

| Topic | Payload | Thiết bị |
|-------|---------|----------|
| home/control/device/1 | "ON" hoặc "OFF" | Đèn Phòng Khách |
| home/control/device/2 | "ON" hoặc "OFF" | Đèn Phòng Ngủ |
| home/control/device/3 | "ON" hoặc "OFF" | Đèn Bếp |
| home/control/device/4 | "ON" hoặc "OFF" | Đèn Sân Vườn |
| home/control/device/5 | {"speed": N} (N=0..3) | Quạt Phòng Khách |
| home/control/device/6 | {"speed": N} | Quạt Phòng Ngủ |
| home/control/device/7 | {"speed": N} | Quạt Bếp |
| home/control/device/8 | {"speed": N} | Quạt Thông Gió |
| home/control/device/11 | "LOCK" hoặc "UNLOCK" | Cửa Chính |
| home/control/device/12 | "ON" / "OFF" / "BEEP" | Loa Buzzer |

ESP32 subscribe: `home/control/device/#`
PWM mapping: speed 1 -> 80 | speed 2 -> 175 | speed >=3 -> 255

### 3.2 ESP32 gửi lên Backend (Sensors)

| Topic | Payload JSON | Mô tả |
|-------|-------------|-------|
| home/sensors/9 | {"temp": 28.5, "humi": 65.0} | DHT11 mỗi 5 giây |
| home/sensors/10 | {"light": 2500} | Cảm biến ánh sáng mỗi 5 giây |

Backend subscribe: `home/sensors/#`
Backend lưu vào `device_history` và cập nhật `devices.status`

---

## 4. Cấu Trúc Thư Mục Dự Án

```
PBL5_DoAnNhaThongMinh/
├── backend/
│   ├── main.py                 <- Entry point: init app, register routers
│   ├── core/
│   │   ├── config.py           <- MQTT_BROKER, MQTT_PORT, DB_NAME, SERVER_PORT
│   │   └── database.py         <- SQLite schema, init_db(), CRUD functions
│   ├── models/
│   │   └── schemas.py          <- Pydantic request/response models
│   ├── routers/
│   │   ├── system_routers.py   <- GET /api/health, GET /api/time
│   │   ├── status_routers.py   <- GET /api/status/...
│   │   ├── sensor_routers.py   <- GET /api/sensors/...
│   │   ├── control_routers.py  <- POST /api/control/...
│   │   ├── schedule_routers.py <- POST/GET/DELETE /api/schedules/...
│   │   ├── alarm_routers.py    <- POST/GET/DELETE /api/alarms/...
│   │   ├── bulk_routers.py     <- POST /api/bulk/...
│   │   ├── weather_routers.py  <- GET /api/weather/...
│   │   └── context_routers.py  <- GET/POST /api/context/...
│   ├── services/
│   │   └── mqtt_service.py     <- MQTTManager class (paho-mqtt)
│   └── workers/
│       └── worker.py           <- alarm_worker, buzzer_alarm_worker, cleanup_worker
│
├── hardware/
│   └── main/
│       ├── main.ino            <- setup() + loop()
│       ├── devices_config.h    <- struct Device, myDevices[12]
│       ├── wifi_mqtt.h         <- WiFi + MQTT + callback()
│       ├── light_device.h      <- control_light()
│       ├── fan_device.h        <- control_fan() + JSON parse
│       ├── door_device.h       <- control_door() + Servo
│       ├── buzzer_device.h     <- control_buzzer(), beep_alarm()
│       ├── sensor_device.h     <- read_and_send_sensors() DHT11
│       └── light_sensor_device.h <- read_and_send_light_sensors()
│
├── frontend/                   <- Flutter App
├── ai_engine/                  <- AI engine (chua tich hop)
└── requirements.txt
```

---

## 5. Chi Tiết Backend

### 5.1 Khởi động (main.py - lifespan)

```
1. init_db()              -> Tạo bảng SQLite, nạp dữ liệu phòng/thiết bị
2. mqtt_service.start()   -> Kết nối MQTT Broker, subscribe "home/sensors/#"
3. alarm_worker()         -> Background: quét schedules mỗi 5 giây
4. buzzer_alarm_worker()  -> Background: quét alarms mỗi 30 giây
5. cleanup_worker()       -> Background: xóa lịch sử cũ mỗi 24 giờ
```

### 5.2 Database Schema (SQLite)

**Bảng rooms:**
```sql
CREATE TABLE rooms (
    id   INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    slug TEXT NOT NULL UNIQUE
)
```

**Bảng devices:**
```sql
CREATE TABLE devices (
    id      INTEGER PRIMARY KEY,
    room_id INTEGER,
    name    TEXT,
    type    TEXT,    -- "light","fan","sensor","light_sensor","door_lock","buzzer"
    pin     INTEGER,
    status  TEXT,
    FOREIGN KEY (room_id) REFERENCES rooms(id)
)
```

**Bảng device_history:**
```sql
CREATE TABLE device_history (
    log_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id INTEGER,
    status    TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
)
-- Xóa tự động bản ghi cũ hơn 7 ngày
```

**Bảng schedules:**
```sql
CREATE TABLE schedules (
    schedule_id  INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id    INTEGER,
    command      TEXT,           -- "ON", "OFF", hoặc '{"speed": 2}'
    trigger_time DATETIME,       -- "YYYY-MM-DD HH:MM:SS"
    status       TEXT DEFAULT 'PENDING',  -- "PENDING", "DONE", "CANCELLED"
    created_at   DATETIME DEFAULT CURRENT_TIMESTAMP
)
```

**Bảng alarms:**
```sql
CREATE TABLE alarms (
    alarm_id   TEXT PRIMARY KEY,  -- "alarm_xxxxxx" (uuid hex 6 ký tự)
    time       TEXT NOT NULL,     -- "HH:MM"
    repeat     BOOLEAN DEFAULT 0,
    label      TEXT,
    status     TEXT DEFAULT 'active',  -- "active", "done", "cancelled"
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
)
```

### 5.3 Database Functions (database.py)

```python
get_db_connection()           -> sqlite3.Connection (row_factory=Row)
init_db()                     -> Tạo bảng + nạp dữ liệu seed
insert_sensor_data(id, v1, v2) -> UPDATE devices + INSERT device_history
get_latest_sensor_data(id)    -> dict {device_id, value1, value2, timestamp, raw_status}
get_device_by_id(id)          -> dict | None
get_devices_by_type(type)     -> list[dict]
get_devices_by_room(room_id)  -> list[dict]
get_room_by_slug(slug)        -> dict | None
update_device_status(id, st)  -> bool
get_sensor_history(id, limit, from_time, to_time) -> list[dict]
delete_old_history()          -> Xóa device_history cũ hơn 7 ngày
```

**Lưu ý get_latest_sensor_data():** Parse status_str:
- Nếu có "°C" -> split " - " -> val1=temp, val2=humi
- Else -> val1=float(status_str), val2=0

### 5.4 MQTT Service (services/mqtt_service.py)

```python
class MQTTManager:
    broker = "172.20.10.2"
    port = 1883
    
    start():
        connect(broker, port)
        loop_start()
    
    on_connect():
        subscribe("home/sensors/#")
    
    on_message(topic, payload):
        device_id = int(topic.split("/")[-1])
        data = json.loads(payload)
        if "temp" in data:
            insert_sensor_data(device_id, data["temp"], data["humi"])
        elif "light" in data:
            insert_sensor_data(device_id, data["light"], 0)
    
    publish_command(device_id, command):
        publish(f"home/control/device/{device_id}", command)
```

### 5.5 Background Workers (workers/worker.py)

```
alarm_worker (asyncio, mỗi 5 giây):
  SELECT * FROM schedules WHERE status='PENDING' AND trigger_time <= now
  -> publish MQTT
  -> UPDATE schedules SET status='DONE'
  -> UPDATE devices SET status=cmd

buzzer_alarm_worker (asyncio, mỗi 30 giây):
  SELECT * FROM alarms WHERE status='active' AND time = HH:MM_now
  -> publish "ON" tới home/control/device/12
  -> Nếu repeat=0: UPDATE alarms SET status='done'

cleanup_worker (asyncio, mỗi 86400 giây):
  DELETE FROM device_history WHERE timestamp < now - 7 days
```

### 5.6 Pydantic Request Schemas (models/schemas.py)

```python
LightControlRequest:   state: str              # "on" / "off"
FanControlRequest:     state: str, speed: Optional[int]  # 0-3
FanAdjustRequest:      action: str             # "up" / "down"
DoorControlRequest:    action: str             # "lock" / "unlock"
BuzzerControlRequest:  state: str              # "on" / "off"
AutoModeRequest:       command: str            # "ON" / "OFF"
ScheduleSetRequest:    device_id: int, command: str, time: str
TimerSetRequest:       device_id: int, command: str, delay_minutes: int
BatchTimerRequest:     device_type: str, command: str, delay_minutes: int
AlarmSetRequest:       time: str, repeat: bool=False, label: Optional[str]
BulkAction:            device_id: int, command: str
BulkControlRequest:    actions: list[BulkAction]
BulkAllRequest:        state: str
ContextConfirmRequest: pending_id: str, confirm: bool
```

### 5.7 Toàn Bộ 30 API Endpoints

**Hệ thống (/api):**
```
GET  /api/health     -> {status, message, data:{version, mqtt_connected}}
GET  /api/time       -> {time, date, context}  [KHÔNG có wrapper status/data]
```

**Điều khiển (/api/control):**
```
POST /api/control/light/all          body:{state}        -> MQTT "ON"/"OFF" tới ID 1,2,3,4
POST /api/control/light/{device_id}  body:{state}        -> MQTT "ON"/"OFF"
POST /api/control/fan/{device_id}    body:{state,speed}  -> MQTT {"speed":N}
POST /api/control/fan/{device_id}/adjust body:{action}   -> MQTT {"speed":N+-1}
POST /api/control/door/{device_id}   body:{action}       -> MQTT "LOCK"/"UNLOCK"
POST /api/control/buzzer/{device_id} body:{state}        -> MQTT "ON"/"OFF"
POST /api/control/auto/{type}        body:{command}      -> MQTT tới home/control/auto/{type}
```

**Trạng thái (/api/status):**
```
GET /api/status/door                 -> device_id=11 status
GET /api/status/rooms/{room_slug}    -> tất cả thiết bị trong phòng
GET /api/status/devices              -> tất cả 12 thiết bị
GET /api/status/devices/{device_id}  -> một thiết bị
```

**Cảm biến (/api/sensors):**
```
GET /api/sensors/latest/{device_id}           -> dữ liệu mới nhất
GET /api/sensors/all                          -> DHT11 + ánh sáng
GET /api/sensors/history/{device_id}?limit=50&from=...&to=...
```

**Hẹn giờ (/api/schedules):**
```
POST   /api/schedules/set          body:{device_id, command, time}
POST   /api/schedules/set-timer    body:{device_id, command, delay_minutes}
POST   /api/schedules/batch        body:{device_type, command, delay_minutes}
GET    /api/schedules/active
DELETE /api/schedules/cancel-all
DELETE /api/schedules/{schedule_id}
```

**Báo thức (/api/alarms):**
```
POST   /api/alarms/set       body:{time, repeat, label}
GET    /api/alarms/active
DELETE /api/alarms/{alarm_id}
```

**Bulk (/api/bulk):**
```
POST /api/bulk/control   body:{actions:[{device_id,command},...]}
POST /api/bulk/all       body:{state}  -> tất cả trừ sensor, door_lock
```

**Thời tiết (/api/weather):**
```
GET /api/weather/current?city=Da+Nang   -> OpenWeatherMap API
```

**Ngữ cảnh (/api/context):**
```
GET  /api/context/suggestions   -> phân tích sensor + giờ -> gợi ý
POST /api/context/confirm       body:{pending_id, confirm}
```

**Context rules:**
```
temp > 30°C                     -> gợi ý bật Quạt ID 5, speed 3
light < 100 AND hour >= 17      -> gợi ý bật Đèn ID 1
hour >= 23                      -> gợi ý tắt tất cả
context values: "hot", "dark", "sleep", "normal"
```

---

## 6. Chi Tiết Hardware (ESP32)

### 6.1 Luồng thực thi

```
setup():
  setup_lights()          -> pinMode OUTPUT, LOW cho pin 18,19,21,22
  setup_fans()            -> pinMode OUTPUT, LOW cho pin 26,25,33,32
  setup_sensors()         -> Khởi tạo DHT11 tại pin 4
  setup_light_sensors()   -> pinMode INPUT tại pin 35
  setup_door()            -> ESP32PWM timer, Servo attach pin 13, write(0)=đóng
  setup_pins()            -> pinMode OUTPUT buzzer pin 16
  setup_wifi_mqtt()       -> WiFi.begin, setServer, setCallback(callback)

loop():
  duy_tri_mqtt()              -> Reconnect WiFi/MQTT + client.loop()
  read_and_send_sensors()     -> Đọc DHT11, gửi MQTT mỗi 5000ms (millis)
  read_and_send_light_sensors() -> Đọc LDR, gửi MQTT mỗi 5000ms (millis)
```

### 6.2 MQTT Callback (wifi_mqtt.h)

```
callback(topic, payload):
  device_id = int(topic cuối cùng sau "/")

  1-4   -> control_light(id, msg)
    "ON"  -> digitalWrite(pin, HIGH)
    "OFF" -> digitalWrite(pin, LOW)

  5-8   -> control_fan(id, msg)
    JSON parse: speed = doc["speed"]
    speed 0 -> analogWrite(pin, 0)
    speed 1 -> analogWrite(pin, 80)
    speed 2 -> analogWrite(pin, 175)
    speed >=3 -> analogWrite(pin, 255)

  11    -> control_door(id, msg)
    "UNLOCK" -> doorServo.write(90)
    "LOCK"   -> doorServo.write(0)

  12    -> control_buzzer(id, msg)
    "ON"   -> digitalWrite(pin, HIGH)
    "OFF"  -> digitalWrite(pin, LOW)
    "BEEP" -> beep_alarm(id): 3 tieng bip (200ms HIGH, 200ms LOW) x 3
```

### 6.3 Cấu trúc dữ liệu (devices_config.h)

```cpp
struct Device { int id; String type; int pin; };

Device myDevices[12] = {
  {1,"light",18}, {2,"light",19}, {3,"light",21}, {4,"light",22},
  {5,"fan",26},   {6,"fan",25},   {7,"fan",33},   {8,"fan",32},
  {9,"sensor",4}, {10,"light_sensor",35},
  {11,"door_lock",13}, {12,"buzzer",16}
};
```

### 6.4 Sensor Format

```
DHT11 (device_id=9):
  topic:   home/sensors/9
  payload: {"temp": 28.5, "humi": 65.0}
  rate:    mỗi 5000ms (non-blocking millis)

Light sensor (device_id=10):
  topic:   home/sensors/10
  payload: {"light": 2500}
  range:   0 (sáng) đến 4095 (tối) - ADC 12-bit ESP32
  rate:    mỗi 5000ms (non-blocking millis)
```

---

## 7. Ràng Buộc Quan Trọng

### 7.1 Case sensitivity của MQTT payload

```
Đèn  (1-4) : "ON" / "OFF"          <- UPPERCASE
Quạt (5-8) : {"speed": N}           <- JSON int 0-3
Cửa  (11)  : "LOCK" / "UNLOCK"     <- UPPERCASE
Buzzer(12) : "ON" / "OFF" / "BEEP" <- UPPERCASE
```

### 7.2 Thứ tự route FastAPI

```python
# Route cố định PHẢI đứng TRƯỚC route có {param}
@router.post("/light/all")         # TRƯỚC
@router.post("/light/{device_id}") # SAU

@router.get("/door")               # TRƯỚC
@router.get("/devices/{id}")       # SAU

@router.delete("/cancel-all")      # TRƯỚC
@router.delete("/{schedule_id}")   # SAU
```

### 7.3 Sensor type check - quan trọng

```python
# SAI (chỉ check "sensor" -> bỏ sót light_sensor):
if device["type"] != "sensor": raise 404

# ĐÚNG:
if device["type"] not in ["sensor", "light_sensor"]: raise 404
```

### 7.4 Response format chuẩn

```json
// Thành công:
{"status": "success", "message": "...", "data": {...}}

// Lỗi:
{"status": "error", "error_code": "DEVICE_NOT_FOUND", "message": "..."}

// Ngoại lệ: GET /api/time không có wrapper (inconsistency đã biết)
```

### 7.5 Known Issues

| Vấn đề | Mô tả |
|--------|-------|
| Auto mode | ESP32 không subscribe home/control/auto/# -> endpoint /api/control/auto/{type} không có tác dụng thực |
| /api/time | Thiếu wrapper {"status","data"} so với chuẩn |
| Sensor DB storage | Lưu dạng string "28.5 - 65%", cần parse khi đọc |
| Context pending | Lưu RAM -> mất khi restart server |
| WiFi credentials | Hardcoded trong wifi_mqtt.h |

---

## 8. Luồng End-to-End

### 8.1 Điều khiển thiết bị

```
Flutter: POST /api/control/light/1 {"state":"on"}
  -> Backend validate, get_device_by_id(1), check type="light"
  -> update_device_status(1, "on")
  -> mqtt_service.publish_command(1, "ON")
  -> Broker forward
  -> ESP32 callback: device_id=1, control_light(1,"ON")
  -> digitalWrite(18, HIGH)
  -> Đèn BẬT
```

### 8.2 Đọc cảm biến

```
ESP32 (mỗi 5s): DHT11 read -> publish home/sensors/9 {"temp":28.5,"humi":65}
  -> Broker forward
  -> Backend on_message: insert_sensor_data(9, 28.5, 65)
      -> UPDATE devices SET status="28.5 - 65%" WHERE id=9
      -> INSERT INTO device_history

Flutter: GET /api/sensors/latest/9
  -> get_latest_sensor_data(9)
  -> Query device_history LIMIT 1
  -> Parse "28.5 - 65%" -> temp=28.5, humi=65
  -> Return {"temperature":{"value":28.5,"unit":"C"}, "humidity":{"value":65,"unit":"%"}}
```

### 8.3 Hẹn giờ

```
Flutter: POST /api/schedules/set-timer {"device_id":1,"command":"OFF","delay_minutes":30}
  -> trigger_time = now + 30min
  -> INSERT INTO schedules
  -> Return schedule_id

alarm_worker (mỗi 5s):
  SELECT WHERE status='PENDING' AND trigger_time <= now
  -> publish "OFF" home/control/device/1
  -> UPDATE schedules status='DONE'
  -> UPDATE devices status='off'
  -> ESP32 tắt đèn
```

### 8.4 Báo thức

```
Flutter: POST /api/alarms/set {"time":"06:30","repeat":false,"label":"Dậy đi học"}
  -> INSERT INTO alarms

buzzer_alarm_worker (mỗi 30s):
  Lúc 06:30: SELECT WHERE status='active' AND time='06:30'
  -> publish "ON" home/control/device/12
  -> ESP32 bật buzzer kêu liên tục
  -> UPDATE alarms SET status='done' (nếu repeat=false)
```
