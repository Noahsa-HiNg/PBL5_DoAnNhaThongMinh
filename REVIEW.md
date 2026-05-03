# 📋 NHẬN XÉT CHI TIẾT — DỰ ÁN PBL5: NHÀ THÔNG MINH

> **Người nhận xét:** AI Code Review  
> **Ngày:** 2026-05-02  
> **Phiên bản hệ thống:** Smart Home API v2.0  
> **Trường:** Đại học Bách Khoa Đà Nẵng

---

## 1. TỔNG QUAN DỰ ÁN

Dự án xây dựng một hệ thống **Nhà Thông Minh (Smart Home)** hoàn chỉnh theo kiến trúc 3 tầng:

```
Flutter App  <── HTTP REST ──>  FastAPI Backend  <── MQTT ──>  ESP32
                                       │
                                  SQLite DB
                                       │
                              AI Agent (Dialog Manager)
```

Hệ thống quản lý **12 thiết bị** phân bổ trong 4 phòng (Phòng Khách, Phòng Ngủ, Nhà Bếp, Sân Vườn), bao gồm: 4 đèn, 4 quạt, 2 cảm biến, 1 khóa cửa, 1 loa.

---

## 2. ĐIỂM MẠNH CỦA DỰ ÁN

### 2.1 Kiến Trúc Hệ Thống — ⭐⭐⭐⭐½

- **Phân tầng rõ ràng và hợp lý.** Backend, hardware, AI agent được tổ chức thành các module độc lập, dễ mở rộng và bảo trì.
- **Tài liệu kiến trúc xuất sắc.** File `PROJECT_ARCHITECTURE.md` (585 dòng) là tài liệu kỹ thuật chất lượng cao, mô tả đầy đủ schema DB, API endpoints, luồng dữ liệu MQTT và các ràng buộc quan trọng — đây là thực hành tốt hiếm gặp ở cấp độ đồ án sinh viên.
- **Giao tiếp MQTT chuẩn.** Topic naming rõ ràng (`home/control/device/#`, `home/sensors/#`), payload format nhất quán.

### 2.2 Backend FastAPI — ⭐⭐⭐⭐

**Thiết kế Router:**
- Tổ chức theo domain tốt: `control_routers`, `sensor_routers`, `schedule_routers`, `alarm_routers`, `bulk_routers`, `context_routers`, `weather_routers`.
- Tuân thủ đúng quy tắc FastAPI: route cố định (`/light/all`) đặt trước route có param (`/light/{device_id}`) — một lỗi thường gặp đã được phòng ngừa.
- 30 endpoints bao phủ toàn bộ use case của hệ thống.

**Response format nhất quán:**
```json
{"status": "success", "message": "...", "data": {...}}
{"status": "error", "error_code": "DEVICE_NOT_FOUND", "message": "..."}
```

**Background Workers (workers/worker.py):**
- `alarm_worker` — quét schedule mỗi 5 giây, xử lý quạt riêng biệt với JSON `{"speed": N}`, thiết bị khác với chuỗi `ON/OFF`. Logic phân nhánh theo `device_type` rất chu đáo.
- `buzzer_alarm_worker` — khi báo thức kích hoạt, tự động bật loa + đèn + quạt, sau 60 giây tự tắt — đây là UX tốt.
- `cleanup_worker` — xóa lịch sử cũ hơn 7 ngày mỗi 24h, tránh phình DB.

**Lifespan Management:**
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    mqtt_service.start()
    asyncio.create_task(alarm_worker())
    ...
    yield
    mqtt_service.client.loop_stop()
```
Sử dụng `asynccontextmanager` (FastAPI hiện đại) thay vì `on_event` deprecated — đúng chuẩn.

### 2.3 Database Layer — ⭐⭐⭐½

- Schema SQLite được thiết kế tốt với 5 bảng: `rooms`, `devices`, `device_history`, `schedules`, `alarms`.
- Seed data được nạp tự động khi khởi động với ID cứng — đúng pattern cho embedded system.
- `get_sensor_history()` hỗ trợ filter theo `from_time`, `to_time`, `limit` — linh hoạt.
- Dùng `conn.row_factory = sqlite3.Row` giúp truy cập field bằng tên thay vì index — code dễ đọc hơn.
- Hàm `delete_old_history()` bảo vệ storage.

### 2.4 Hardware ESP32 — ⭐⭐⭐⭐

- **Non-blocking design:** dùng `millis()` thay vì `delay()` trong loop, đảm bảo MQTT responsive.
- **Reconnect logic:** `duy_tri_mqtt()` tự động reconnect WiFi/MQTT bằng timer (không block CPU) — xử lý Watchdog Timeout đúng cách.
- **Random Client ID:** tránh MQTT kick session cũ khi reconnect.
- **File tổ chức tốt:** mỗi thiết bị có header riêng (`fan_device.h`, `light_device.h`...) — clean code.
- **PWM mapping cụ thể:** speed 1→80, speed 2→175, speed≥3→255, cân nhắc đến đặc tính cơ học của motor.

### 2.5 AI Agent (Dialog Manager) — ⭐⭐⭐⭐

- `dialog_manager.py` (883 dòng) là thành phần phức tạp nhất, thể hiện hiểu biết sâu về NLP/dialog systems.
- Quản lý dialog state đầy đủ: `pending_action`, `waiting_room`, TTL tracking để tự động hủy context cũ.
- Hỗ trợ đa intent: `control_device`, `query_status`, `query_sensor`, `query_time`, `query_weather`, `schedule_set`, `alarm_set`, `context_hot/cold/sleep`...
- **Fallback graceful:** khi API lỗi, DM vẫn hoạt động bằng mock/local state — không crash.
- `_extract_slots()` xử lý Orphan I- tag, multi-device, multi-room — robust với NLU output không hoàn hảo.

### 2.6 Test Coverage — ⭐⭐⭐⭐½

`test_api.py` (394 dòng) có bộ test toàn diện:
- **~60 test cases** bao phủ tất cả endpoints.
- Test cả **happy path** và **error path** (400, 404).
- Output màu sắc (GREEN/RED/YELLOW) dễ đọc trên terminal.
- Thống kê pass/fail/skip rate cuối cùng.

---

## 3. ĐIỂM YẾU VÀ VẤN ĐỀ CẦN CẢI THIỆN

### 3.1 Bảo Mật — ⚠️ NGHIÊM TRỌNG

#### a) Hardcode credentials trong source code
```c
// wifi_mqtt.h — NGUY HIỂM
const char* ssid = "hieu";
const char* password = "123456719";
const char* mqtt_server = "172.20.10.3";
```
**Rủi ro:** Nếu upload lên GitHub public, credentials bị lộ ngay lập tức.  
**Khuyến nghị:** Dùng file `credentials.h` (thêm vào `.gitignore`) hoặc NVS của ESP32.

#### b) CORS quá rộng
```python
allow_origins=["*"]  # Cho phép tất cả origin
```
**Khuyến nghị:** Giới hạn origin cụ thể khi deploy thật.

#### c) Không có Authentication
Không có JWT hay bất kỳ cơ chế xác thực nào trên các API endpoint. Bất kỳ ai trong cùng mạng đều có thể điều khiển toàn bộ thiết bị.

#### d) MQTT không có authentication
Mosquitto broker chạy không có username/password. Bất kỳ client nào trong mạng đều connect và publish/subscribe được.

### 3.2 Concurrency & Thread Safety — ⚠️ QUAN TRỌNG

#### a) SQLite với `check_same_thread=False`
Nhiều asyncio workers + FastAPI handlers cùng ghi DB mà không có locking → **race condition tiềm ẩn** khi tải cao.  
**Khuyến nghị:** Dùng `aiosqlite` hoặc connection pool với proper locking.

#### b) `pending_actions` dict trong RAM
```python
pending_actions = {}  # Module-level dict — mất khi restart, không share giữa workers
```
**Khuyến nghị:** Dùng Redis hoặc bảng `pending_suggestions` trong SQLite.

#### c) Multiple `_auto_off()` tasks
Nếu báo thức kích hoạt nhiều lần trong vòng 60 giây, nhiều `_auto_off` tasks chạy song song → hành vi không xác định.

### 3.3 Data Model & Consistency — ⚠️

#### a) Lưu sensor data dạng string phải parse lại
```python
status_text = f"{value1}°C - {value2}%"  # Lưu string, parse lại khi đọc
```
**Vấn đề:** Fragile parsing, dễ lỗi nếu format thay đổi.  
**Khuyến nghị:** Lưu `value1` và `value2` vào 2 column riêng trong `device_history`.

#### b) Status field dùng chung cho nhiều type
Bảng `devices` dùng 1 field `status TEXT` cho tất cả loại thiết bị — không có schema validation → dễ lưu sai kiểu dữ liệu.

#### c) Timezone không xử lý
```python
datetime.now()  # Local time, không timezone-aware
```
**Khuyến nghị:** Dùng `datetime.now(timezone.utc)` nhất quán.

### 3.4 Error Handling — ⚠️

- **Bare `except: pass`** ở nhiều chỗ trong `database.py` — nuốt lỗi silently.
- **Không rollback khi lỗi giữa vòng for** trong `worker.py`.
- **MQTT publish không kiểm tra kết nối:** nếu broker mất, lệnh mất trong im lặng nhưng DB đã cập nhật → **state drift**.

### 3.5 API Inconsistencies — 📝

| Endpoint | Vấn đề |
|----------|--------|
| `GET /api/time` | Thiếu wrapper `{"status","data"}` so với các endpoint khác |
| `POST /api/control/auto/{type}` | ESP32 không subscribe `home/control/auto/#` → endpoint vô tác dụng |
| `GET /api/context/suggestions` | `pending_id_counter` sẽ trùng ID sau khi dict bị xóa |
| `POST /api/alarms/set` | Không validate format `HH:MM` nghiêm ngặt |

### 3.6 Frontend — 🔴 THIẾU HOÀN TOÀN

```
frontend/
└── temp.txt   ← Chỉ có 1 file tạm
```
Flutter app được đề cập trong kiến trúc nhưng **chưa được implement** trong repository. Đây là thiếu sót lớn nhất.

### 3.7 AI Engine — 📝 Chưa Tích Hợp

STT engine có model đã train (adapter weights, tokenizer) nhưng **chưa có inference code** để chạy thực tế. Không có API endpoint để nhận audio từ Flutter.

### 3.8 Requirements.txt — 📝

```
torch==2.1.0+cu118  ← Package ML nặng ~2GB không cần cho backend
```
Thiếu các package core như `fastapi`, `uvicorn`, `paho-mqtt`. Nên tách thành 2 file riêng.

---

## 4. ĐÁNH GIÁ THEO TIÊU CHÍ

| Tiêu chí | Điểm | Nhận xét |
|----------|------|----------|
| **Ý tưởng & Tính thực tiễn** | 9/10 | Hệ thống nhà thông minh hoàn chỉnh, thiết thực |
| **Kiến trúc hệ thống** | 8/10 | 3-tier rõ ràng, tài liệu xuất sắc |
| **Chất lượng Backend** | 8/10 | FastAPI chuẩn, đủ endpoint, thiếu auth |
| **Chất lượng Hardware** | 8.5/10 | Non-blocking, reconnect tốt |
| **AI/NLP Component** | 7.5/10 | Dialog Manager ấn tượng, STT chưa tích hợp |
| **Bảo mật** | 4/10 | Hardcode credentials, không auth, CORS mở |
| **Testing** | 8.5/10 | Test suite toàn diện, ~60 cases |
| **Tài liệu** | 9/10 | PROJECT_ARCHITECTURE.md rất tốt |
| **Frontend** | 1/10 | Chưa implement |
| **Tổng thể** | **7.5/10** | |

---

## 5. ĐỀ XUẤT CẢI THIỆN THEO ƯU TIÊN

### 🔴 Ưu tiên cao

1. **Di chuyển credentials ra ngoài code** — tạo `credentials.h` trong `.gitignore`
2. **Thêm JWT Authentication** cho các endpoint điều khiển
3. **Kiểm tra MQTT connection** trước khi `publish_command()`
4. **Sửa schema lưu sensor data** — thêm column `value1 REAL`, `value2 REAL`

### 🟡 Ưu tiên trung bình

5. **Sử dụng `aiosqlite`** thay vì sqlite3 đồng bộ trong async context
6. **Chuyển `pending_actions`** sang SQLite với expiry time
7. **Thêm logging** đúng cách thay vì `print()`
8. **Validate time format** nghiêm ngặt cho alarm endpoint
9. **Chuẩn hóa `GET /api/time`** response format

### 🟢 Ưu tiên thấp (tính năng mới)

10. **Hoàn thiện Frontend Flutter** — phần thiếu sót lớn nhất
11. **Tích hợp STT Engine** — thêm WebSocket endpoint cho voice control
12. **Thêm MQTT Authentication** trong `mosquitto.conf`
13. **Tách `requirements.txt`** thành backend và AI riêng
14. **Implement `/api/control/auto/{type}`** phía ESP32

---

## 6. ĐIỂM ĐẶC BIỆT NỔI BẬT

> Có một số điểm kỹ thuật vượt trội hơn mức đồ án sinh viên thông thường:

1. **Dialog Manager v9** — Hệ thống quản lý dialog state với TTL, pending actions, multi-turn context resolution là công trình NLP nghiêm túc. Việc port từ Jupyter Notebook sang production code với dependency injection (`api_client`) thể hiện kỹ năng software engineering tốt.

2. **Background Worker với fan-specific logic** — `alarm_worker` xử lý riêng biệt quạt (JSON payload) vs đèn/buzzer (string payload) dựa trên `device_type` từ DB join — chi tiết kỹ thuật rất cẩn thận.

3. **Non-blocking WiFi reconnect trên ESP32** — Giải quyết đúng vấn đề Watchdog Timeout bằng `millis()` thay vì `while(WiFi.reconnect())` blocking trong loop.

4. **Tài liệu kiến trúc chuẩn production** — `PROJECT_ARCHITECTURE.md` với đầy đủ bảng thiết bị, MQTT topic mapping, API spec, known issues — thực hành tốt nhất mà nhiều team chuyên nghiệp không làm được.

---

## 7. KẾT LUẬN

Dự án PBL5 Nhà Thông Minh là một hệ thống **IoT hoàn chỉnh và nghiêm túc**, thể hiện sự hiểu biết tốt về kiến trúc microservice nhúng, giao thức MQTT, NLP/Dialog Management và REST API design.

**Điểm trừ chính** là frontend chưa hoàn thiện, bảo mật cần cải thiện đáng kể, và một số vấn đề về thread safety trong môi trường concurrent.

Đây là nền tảng vững chắc cho một sản phẩm IoT thực tế. Với việc bổ sung Authentication, hoàn thiện Frontend Flutter và tích hợp STT, hệ thống có thể đạt mức **demo-ready production quality**.

---
*File nhận xét được tạo tự động bằng phân tích toàn bộ source code của dự án.*
