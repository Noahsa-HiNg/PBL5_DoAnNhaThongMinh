# 📘 PBL5 Smart Home — REST API Specification v2.0

> **Kiến trúc**: Flutter App ↔ **REST API (HTTP)** ↔ FastAPI Backend ↔ **MQTT** ↔ ESP32
> 
> **Base URL**: `http://<server_ip>:5000`
> 
> **Tài liệu này mô tả toàn bộ REST API giữa App và Backend.** Phần MQTT (Backend ↔ ESP32) được mô tả riêng ở [Phụ lục A](#phụ-lục-a-mqtt-topics-backend--esp32).

---

## 📑 Mục Lục

| # | Nhóm | Prefix |
|---|------|--------|
| 1 | [Hệ thống](#1️⃣-hệ-thống) | `/api` |
| 2 | [Điều khiển thiết bị](#2️⃣-điều-khiển-thiết-bị-device-control) | `/api/control` |
| 3 | [Trạng thái thiết bị](#3️⃣-trạng-thái-thiết-bị-device-status) | `/api/status` |
| 4 | [Cảm biến](#4️⃣-cảm-biến-sensors) | `/api/sensors` |
| 5 | [Hẹn giờ & Lịch trình](#5️⃣-hẹn-giờ--lịch-trình-schedules) | `/api/schedules` |
| 6 | [Báo thức](#6️⃣-báo-thức-alarms) | `/api/alarms` |
| 7 | [Điều khiển hàng loạt](#7️⃣-điều-khiển-hàng-loạt-bulk-control) | `/api/bulk` |
| 8 | [Thời tiết](#8️⃣-thời-tiết-weather) | `/api/weather` |
| 9 | [Gợi ý ngữ cảnh](#9️⃣-gợi-ý-ngữ-cảnh-context-suggestions) | `/api/context` |
| 10 | [Mã lỗi](#🔟-bảng-mã-lỗi-error-codes) | — |
| A | [MQTT Topics (Backend ↔ ESP32)](#phụ-lục-a-mqtt-topics-backend--esp32) | — |

---

## Quy Ước Chung

### Response Format
Tất cả response đều trả JSON với cấu trúc:

```json
// Thành công
{
  "status": "success",
  "message": "Mô tả hành động",
  "data": { ... }
}

// Lỗi
{
  "status": "error",
  "error_code": "DEVICE_NOT_FOUND",
  "message": "Không tìm thấy thiết bị",
  "timestamp": "2026-04-11T20:00:00"
}
```

### Danh Sách Phòng (Rooms)

| room_id | Tên | Slug |
|---------|-----|------|
| 1 | Phòng Khách | `living_room` |
| 2 | Phòng Ngủ | `bedroom` |
| 3 | Nhà Bếp | `kitchen` |
| 4 | Sân Vườn | `yard` |

### Danh Sách Thiết Bị (Devices)

| device_id | Phòng | Tên | type | GPIO Pin |
|-----------|-------|-----|------|----------|
| 1 | Phòng Khách | Đèn Phòng Khách | `light` | 18 |
| 2 | Phòng Ngủ | Đèn Phòng Ngủ | `light` | 19 |
| 3 | Nhà Bếp | Đèn Bếp | `light` | 21 |
| 4 | Sân Vườn | Đèn Sân Vườn | `light` | 22 |
| 5 | Phòng Khách | Quạt Phòng Khách | `fan` | 26 |
| 6 | Phòng Ngủ | Quạt Phòng Ngủ | `fan` | 25 |
| 7 | Nhà Bếp | Quạt Bếp | `fan` | 33 |
| 8 | Phòng Khách | Quạt Thông Gió | `fan` | 32 |
| 9 | Phòng Khách | Cảm biến Nhiệt ẩm | `sensor` | 4 |
| 10 | Sân Vườn | Cảm biến Ánh sáng | `sensor` | 35 |
| 11 | Phòng Khách | Cửa Chính | `door_lock` | 13 |
| 12 | Phòng Ngủ | Loa (Buzzer) | `buzzer` | 16 |

---

## 1️⃣ Hệ Thống

### `GET /api/health` — Health Check

Kiểm tra server đang hoạt động.

**Response `200`:**
```json
{
  "status": "success",
  "message": "PBL5 Smart Home Server đang hoạt động tốt!",
  "data": {
    "version": "2.0.0",
    "mqtt_connected": true,
    "uptime": "2h 30m"
  }
}
```

### `GET /api/time` — Lấy Thời Gian Hiện Tại

**Response `200`:**
```json
{
  "status": "success",
  "data": {
    "time": "20:30",
    "date": "2026-04-11",
    "context": "evening",
    "timestamp": "2026-04-11T20:30:00"
  }
}
```

> Ghi chú `context`: `"morning"` (5-11h), `"afternoon"` (11-17h), `"evening"` (17-21h), `"night"` (21-5h)

---

## 2️⃣ Điều Khiển Thiết Bị (Device Control)

### 2.1. Đèn (Light)

#### `POST /api/control/light/{device_id}` — Bật/Tắt Đèn

**Path Parameters:**
| Param | Type | Mô tả |
|-------|------|--------|
| `device_id` | int | ID đèn (1–4) |

**Request Body:**
```json
{
  "state": "on"
}
```
| Field | Type | Giá trị | Bắt buộc |
|-------|------|---------|----------|
| `state` | string | `"on"` hoặc `"off"` | ✅ |

**Response `200`:**
```json
{
  "status": "success",
  "message": "Đã gửi lệnh ON tới Đèn Phòng Khách",
  "data": {
    "device_id": 1,
    "name": "Đèn Phòng Khách",
    "state": "on",
    "timestamp": "2026-04-11T20:30:00"
  }
}
```

**Response `400`:**
```json
{
  "status": "error",
  "error_code": "INVALID_ACTION",
  "message": "Lệnh đèn chỉ được là ON hoặc OFF"
}
```

---

#### `POST /api/control/light/all` — Bật/Tắt Tất Cả Đèn

**Request Body:**
```json
{
  "state": "on"
}
```

**Response `200`:**
```json
{
  "status": "success",
  "message": "Đã bật tất cả đèn",
  "data": {
    "affected_devices": [
      {"device_id": 1, "name": "Đèn Phòng Khách", "state": "on"},
      {"device_id": 2, "name": "Đèn Phòng Ngủ", "state": "on"},
      {"device_id": 3, "name": "Đèn Bếp", "state": "on"},
      {"device_id": 4, "name": "Đèn Sân Vườn", "state": "on"}
    ],
    "timestamp": "2026-04-11T20:30:00"
  }
}
```

---

### 2.2. Quạt (Fan)

#### `POST /api/control/fan/{device_id}` — Điều Khiển Quạt

**Path Parameters:**
| Param | Type | Mô tả |
|-------|------|--------|
| `device_id` | int | ID quạt (5–8) |

**Request Body:**
```json
{
  "state": "on",
  "speed": 2
}
```
| Field | Type | Giá trị | Bắt buộc |
|-------|------|---------|----------|
| `state` | string | `"on"` hoặc `"off"` | ✅ |
| `speed` | int | `0`, `1`, `2`, `3` | ❌ (mặc định = 2 khi `state=on`, = 0 khi `state=off`) |

**Response `200`:**
```json
{
  "status": "success",
  "message": "Đã gửi lệnh cho Quạt Phòng Khách",
  "data": {
    "device_id": 5,
    "name": "Quạt Phòng Khách",
    "state": "on",
    "speed": 2,
    "timestamp": "2026-04-11T20:30:00"
  }
}
```

**Response `400`:**
```json
{
  "status": "error",
  "error_code": "INVALID_ACTION",
  "message": "Tốc độ quạt chỉ được từ 0 đến 3"
}
```

---

#### `POST /api/control/fan/{device_id}/adjust` — Tăng/Giảm Tốc Độ Quạt

**Request Body:**
```json
{
  "action": "up"
}
```
| Field | Type | Giá trị | Bắt buộc |
|-------|------|---------|----------|
| `action` | string | `"up"` hoặc `"down"` | ✅ |

> Logic: Lấy speed hiện tại từ DB → +1 hoặc -1 (clamp 0–3) → gửi MQTT

**Response `200`:**
```json
{
  "status": "success",
  "message": "Đã tăng tốc Quạt Phòng Khách lên mức 3",
  "data": {
    "device_id": 5,
    "state": "on",
    "previous_speed": 2,
    "new_speed": 3,
    "timestamp": "2026-04-11T20:30:00"
  }
}
```

---

### 2.3. Khóa Cửa (Door Lock)

#### `POST /api/control/door/{device_id}` — Khóa/Mở Cửa

**Path Parameters:**
| Param | Type | Mô tả |
|-------|------|--------|
| `device_id` | int | ID cửa (11) |

**Request Body:**
```json
{
  "action": "lock"
}
```
| Field | Type | Giá trị | Bắt buộc |
|-------|------|---------|----------|
| `action` | string | `"lock"` hoặc `"unlock"` | ✅ |

**Response `200`:**
```json
{
  "status": "success",
  "message": "Đã khóa Cửa Chính",
  "data": {
    "device_id": 11,
    "name": "Cửa Chính",
    "state": "locked",
    "timestamp": "2026-04-11T20:30:00"
  }
}
```

---

### 2.4. Loa / Buzzer

#### `POST /api/control/buzzer/{device_id}` — Bật/Tắt Loa

**Path Parameters:**
| Param | Type | Mô tả |
|-------|------|--------|
| `device_id` | int | ID loa (12) |

**Request Body:**
```json
{
  "state": "on"
}
```

**Response `200`:**
```json
{
  "status": "success",
  "message": "Đã bật Loa",
  "data": {
    "device_id": 12,
    "name": "Loa",
    "state": "on",
    "timestamp": "2026-04-11T20:30:00"
  }
}
```

---

### 2.5. Chế Độ Tự Động (Auto Mode)

#### `POST /api/control/auto/{type}` — Bật/Tắt Chế Độ Tự Động

**Path Parameters:**
| Param | Type | Mô tả |
|-------|------|--------|
| `type` | string | Loại auto: `"light"`, `"fan"`, `"all"` |

**Request Body:**
```json
{
  "command": "ON"
}
```
| Field | Type | Giá trị | Bắt buộc |
|-------|------|---------|----------|
| `command` | string | `"ON"` hoặc `"OFF"` | ✅ |

**Response `200`:**
```json
{
  "status": "success",
  "message": "Đã bật chế độ tự động cho light",
  "data": {
    "type": "light",
    "auto_mode": "ON",
    "timestamp": "2026-04-11T20:30:00"
  }
}
```

---

## 3️⃣ Trạng Thái Thiết Bị (Device Status)

### `GET /api/status/devices` — Lấy Trạng Thái Tất Cả Thiết Bị

**Response `200`:**
```json
{
  "status": "success",
  "data": {
    "devices": [
      {"device_id": 1, "room_id": 1, "name": "Đèn Phòng Khách", "type": "light", "pin": 18, "state": "on"},
      {"device_id": 2, "room_id": 2, "name": "Đèn Phòng Ngủ", "type": "light", "pin": 19, "state": "off"},
      {"device_id": 5, "room_id": 1, "name": "Quạt Phòng Khách", "type": "fan", "pin": 26, "state": "2"},
      {"device_id": 11, "room_id": 1, "name": "Cửa Chính", "type": "door_lock", "pin": 13, "state": "locked"}
    ],
    "summary": {
      "on": ["Đèn Phòng Khách", "Quạt Phòng Khách"],
      "off": ["Đèn Phòng Ngủ", "Đèn Bếp", "Đèn Sân Vườn", "Quạt Phòng Ngủ", "Quạt Bếp", "Quạt Thông Gió", "Loa"],
      "locked": ["Cửa Chính"]
    },
    "timestamp": "2026-04-11T20:30:00"
  }
}
```

---

### `GET /api/status/devices/{device_id}` — Trạng Thái Thiết Bị Cụ Thể

**Response `200`:**
```json
{
  "status": "success",
  "data": {
    "device_id": 5,
    "room_id": 1,
    "name": "Quạt Phòng Khách",
    "type": "fan",
    "state": "on",
    "speed": 2,
    "timestamp": "2026-04-11T20:30:00"
  }
}
```

**Response `404`:**
```json
{
  "status": "error",
  "error_code": "DEVICE_NOT_FOUND",
  "message": "Không tìm thấy thiết bị với ID 99"
}
```

---

### `GET /api/status/rooms/{room_slug}` — Trạng Thái Theo Phòng

**Path Parameters:**
| Param | Type | Giá trị |
|-------|------|---------|
| `room_slug` | string | `living_room`, `bedroom`, `kitchen`, `yard` |

**Response `200`:**
```json
{
  "status": "success",
  "data": {
    "room": "Phòng Khách",
    "slug": "living_room",
    "devices": [
      {"device_id": 1, "name": "Đèn Phòng Khách", "type": "light", "state": "on"},
      {"device_id": 5, "name": "Quạt Phòng Khách", "type": "fan", "state": "2"},
      {"device_id": 8, "name": "Quạt Thông Gió", "type": "fan", "state": "0"},
      {"device_id": 9, "name": "Cảm biến Nhiệt ẩm", "type": "sensor", "state": "28°C - 65%"},
      {"device_id": 11, "name": "Cửa Chính", "type": "door_lock", "state": "locked"}
    ],
    "timestamp": "2026-04-11T20:30:00"
  }
}
```

**Response `404`:**
```json
{
  "status": "error",
  "error_code": "INVALID_ROOM",
  "message": "Phòng 'garage' không tồn tại"
}
```

---

### `GET /api/status/door` — Trạng Thái Khóa Cửa

**Response `200`:**
```json
{
  "status": "success",
  "data": {
    "device_id": 11,
    "name": "Cửa Chính",
    "state": "locked",
    "timestamp": "2026-04-11T20:30:00"
  }
}
```

---

## 4️⃣ Cảm Biến (Sensors)

### `GET /api/sensors/latest/{device_id}` — Dữ Liệu Cảm Biến Mới Nhất

**Path Parameters:**
| Param | Type | Mô tả |
|-------|------|--------|
| `device_id` | int | `9` (DHT11) hoặc `10` (Ánh sáng) |

**Response `200` (DHT11 — device_id = 9):**
```json
{
  "status": "success",
  "data": {
    "device_id": 9,
    "name": "Cảm biến Nhiệt ẩm",
    "type": "dht11",
    "temperature": {
      "value": 28.5,
      "unit": "°C"
    },
    "humidity": {
      "value": 65,
      "unit": "%"
    },
    "timestamp": "2026-04-11T20:30:00"
  }
}
```

**Response `200` (Ánh sáng — device_id = 10):**
```json
{
  "status": "success",
  "data": {
    "device_id": 10,
    "name": "Cảm biến Ánh sáng",
    "type": "light_sensor",
    "light": {
      "value": 450,
      "unit": "lux"
    },
    "timestamp": "2026-04-11T20:30:00"
  }
}
```

**Response `404`:**
```json
{
  "status": "error",
  "error_code": "SENSOR_ERROR",
  "message": "Không tìm thấy dữ liệu cho thiết bị này"
}
```

---

### `GET /api/sensors/all` — Tất Cả Dữ Liệu Cảm Biến

**Response `200`:**
```json
{
  "status": "success",
  "data": {
    "temperature": {
      "device_id": 9,
      "value": 28.5,
      "unit": "°C"
    },
    "humidity": {
      "device_id": 9,
      "value": 65,
      "unit": "%"
    },
    "light": {
      "device_id": 10,
      "value": 450,
      "unit": "lux"
    },
    "timestamp": "2026-04-11T20:30:00"
  }
}
```

---

### `GET /api/sensors/history/{device_id}` — Lịch Sử Cảm Biến

**Query Parameters:**
| Param | Type | Mặc định | Mô tả |
|-------|------|----------|--------|
| `limit` | int | 50 | Số bản ghi trả về (tối đa 200) |
| `from` | string | — | Thời gian bắt đầu (ISO 8601) |
| `to` | string | — | Thời gian kết thúc (ISO 8601) |

**Ví dụ:** `GET /api/sensors/history/9?limit=10&from=2026-04-11T00:00:00`

**Response `200`:**
```json
{
  "status": "success",
  "data": {
    "device_id": 9,
    "name": "Cảm biến Nhiệt ẩm",
    "total_records": 10,
    "records": [
      {"temperature": 28.5, "humidity": 65, "timestamp": "2026-04-11T20:30:00"},
      {"temperature": 28.2, "humidity": 66, "timestamp": "2026-04-11T20:25:00"},
      {"temperature": 27.8, "humidity": 67, "timestamp": "2026-04-11T20:20:00"}
    ]
  }
}
```

---

## 5️⃣ Hẹn Giờ / Lịch Trình (Schedules)

### `POST /api/schedules/set` — Đặt Hẹn Giờ (Thời Gian Tuyệt Đối)

**Request Body:**
```json
{
  "device_id": 1,
  "command": "ON",
  "time": "2026-04-11T22:00:00"
}
```
| Field | Type | Mô tả | Bắt buộc |
|-------|------|--------|----------|
| `device_id` | int | ID thiết bị | ✅ |
| `command` | string | Lệnh: `"ON"`, `"OFF"`, hoặc JSON quạt `{"speed": 2}` | ✅ |
| `time` | string | Thời gian kích hoạt (ISO 8601) | ✅ |

**Response `201`:**
```json
{
  "status": "success",
  "message": "Đã đặt hẹn giờ cho Đèn Phòng Khách vào lúc 22:00",
  "data": {
    "schedule_id": 15,
    "device_id": 1,
    "device_name": "Đèn Phòng Khách",
    "command": "ON",
    "execute_at": "2026-04-11T22:00:00",
    "status": "PENDING"
  }
}
```

---

### `POST /api/schedules/set-timer` — Hẹn Giờ Theo Khoảng Delay

**Request Body:**
```json
{
  "device_id": 1,
  "command": "OFF",
  "delay_minutes": 30
}
```
| Field | Type | Mô tả | Bắt buộc |
|-------|------|--------|----------|
| `device_id` | int | ID thiết bị | ✅ |
| `command` | string | Lệnh thực thi | ✅ |
| `delay_minutes` | int | Số phút chờ | ✅ |

**Response `201`:**
```json
{
  "status": "success",
  "message": "Đã hẹn giờ tắt Đèn Phòng Khách sau 30 phút",
  "data": {
    "schedule_id": 16,
    "device_id": 1,
    "command": "OFF",
    "execute_at": "2026-04-11T21:00:00",
    "status": "PENDING"
  }
}
```

---

### `POST /api/schedules/batch` — Hẹn Giờ Hàng Loạt

**Request Body:**
```json
{
  "device_type": "light",
  "command": "OFF",
  "delay_minutes": 60
}
```
| Field | Type | Giá trị | Bắt buộc |
|-------|------|---------|----------|
| `device_type` | string | `"light"`, `"fan"`, `"all"` | ✅ |
| `command` | string | Lệnh thực thi | ✅ |
| `delay_minutes` | int | Số phút chờ | ✅ |

**Response `201`:**
```json
{
  "status": "success",
  "message": "Đã hẹn giờ OFF cho 4 thiết bị loại light vào lúc 21:30",
  "data": {
    "affected_count": 4,
    "device_type": "light",
    "execute_at": "2026-04-11T21:30:00",
    "schedules": [
      {"schedule_id": 17, "device_id": 1, "device_name": "Đèn Phòng Khách"},
      {"schedule_id": 18, "device_id": 2, "device_name": "Đèn Phòng Ngủ"},
      {"schedule_id": 19, "device_id": 3, "device_name": "Đèn Bếp"},
      {"schedule_id": 20, "device_id": 4, "device_name": "Đèn Sân Vườn"}
    ]
  }
}
```

---

### `GET /api/schedules/active` — Danh Sách Hẹn Giờ Đang Chờ

**Response `200`:**
```json
{
  "status": "success",
  "data": {
    "total": 2,
    "schedules": [
      {
        "schedule_id": 15,
        "device_id": 1,
        "device_name": "Đèn Phòng Khách",
        "command": "ON",
        "trigger_time": "2026-04-11T22:00:00",
        "status": "PENDING",
        "created_at": "2026-04-11T20:30:00"
      },
      {
        "schedule_id": 16,
        "device_id": 1,
        "device_name": "Đèn Phòng Khách",
        "command": "OFF",
        "trigger_time": "2026-04-11T23:00:00",
        "status": "PENDING",
        "created_at": "2026-04-11T20:30:00"
      }
    ]
  }
}
```

---

### `DELETE /api/schedules/{schedule_id}` — Hủy Hẹn Giờ

**Response `200`:**
```json
{
  "status": "success",
  "message": "Đã hủy hẹn giờ #15"
}
```

**Response `404`:**
```json
{
  "status": "error",
  "error_code": "SCHEDULE_NOT_FOUND",
  "message": "Không tìm thấy hẹn giờ với ID 99"
}
```

---

### `DELETE /api/schedules/cancel-all` — Hủy Tất Cả Hẹn Giờ

**Response `200`:**
```json
{
  "status": "success",
  "message": "Đã hủy 5 hẹn giờ đang chờ",
  "data": {
    "cancelled_count": 5
  }
}
```

---

## 6️⃣ Báo Thức (Alarms)

### `POST /api/alarms/set` — Đặt Báo Thức

**Request Body:**
```json
{
  "time": "06:30",
  "repeat": false,
  "label": "Dậy đi học"
}
```
| Field | Type | Mô tả | Bắt buộc |
|-------|------|--------|----------|
| `time` | string | Giờ báo thức (HH:MM) | ✅ |
| `repeat` | bool | `true` = lặp hàng ngày, `false` = 1 lần | ❌ (mặc định `false`) |
| `label` | string | Nhãn hiển thị | ❌ |

> Khi báo thức kích hoạt → Backend publish MQTT tới buzzer (device_id 12) để kêu.

**Response `201`:**
```json
{
  "status": "success",
  "message": "Đã đặt báo thức lúc 06:30",
  "data": {
    "alarm_id": "alarm_001",
    "time": "06:30",
    "repeat": false,
    "label": "Dậy đi học",
    "next_trigger": "2026-04-12T06:30:00",
    "status": "active"
  }
}
```

---

### `DELETE /api/alarms/{alarm_id}` — Hủy Báo Thức

**Response `200`:**
```json
{
  "status": "success",
  "message": "Đã hủy báo thức alarm_001",
  "data": {
    "alarm_id": "alarm_001",
    "status": "cancelled"
  }
}
```

---

### `GET /api/alarms/active` — Danh Sách Báo Thức Đang Bật

**Response `200`:**
```json
{
  "status": "success",
  "data": {
    "alarms": [
      {
        "alarm_id": "alarm_001",
        "time": "06:30",
        "repeat": false,
        "label": "Dậy đi học",
        "next_trigger": "2026-04-12T06:30:00",
        "status": "active"
      }
    ]
  }
}
```

---

## 7️⃣ Điều Khiển Hàng Loạt (Bulk Control)

### `POST /api/bulk/control` — Điều Khiển Nhiều Thiết Bị Cùng Lúc

**Request Body:**
```json
{
  "actions": [
    {
      "device_id": 1,
      "command": "ON"
    },
    {
      "device_id": 2,
      "command": "OFF"
    },
    {
      "device_id": 5,
      "command": "{\"speed\": 3}"
    },
    {
      "device_id": 11,
      "command": "lock"
    }
  ]
}
```

**Response `200`:**
```json
{
  "status": "success",
  "message": "Đã thực thi 4 lệnh",
  "data": {
    "success": [
      {"device_id": 1, "name": "Đèn Phòng Khách", "command": "ON"},
      {"device_id": 2, "name": "Đèn Phòng Ngủ", "command": "OFF"},
      {"device_id": 5, "name": "Quạt Phòng Khách", "command": "{\"speed\": 3}"},
      {"device_id": 11, "name": "Cửa Chính", "command": "lock"}
    ],
    "failed": [],
    "timestamp": "2026-04-11T20:30:00"
  }
}
```

---

### `POST /api/bulk/all` — Bật/Tắt TẤT CẢ Thiết Bị

**Request Body:**
```json
{
  "state": "off"
}
```

**Response `200`:**
```json
{
  "status": "success",
  "message": "Đã tắt tất cả thiết bị",
  "data": {
    "affected_devices": [
      "Đèn Phòng Khách", "Đèn Phòng Ngủ", "Đèn Bếp", "Đèn Sân Vườn",
      "Quạt Phòng Khách", "Quạt Phòng Ngủ", "Quạt Bếp", "Quạt Thông Gió",
      "Loa"
    ],
    "excluded": ["Cửa Chính", "Cảm biến Nhiệt ẩm", "Cảm biến Ánh sáng"],
    "timestamp": "2026-04-11T20:30:00"
  }
}
```

> Ghi chú: Cảm biến và Cửa bị loại trừ  — cửa cần lock riêng, cảm biến luôn chạy.

---

## 8️⃣ Thời Tiết (Weather)

### `GET /api/weather/current` — Thời Tiết Hiện Tại

**Query Parameters:**
| Param | Type | Mặc định | Mô tả |
|-------|------|----------|--------|
| `city` | string | `"Da Nang"` | Tên thành phố |

**Response `200`:**
```json
{
  "status": "success",
  "data": {
    "city": "Da Nang",
    "temperature": 29.5,
    "humidity": 70,
    "description": "Trời nắng nhẹ",
    "icon_url": "http://openweathermap.org/img/wn/02d@2x.png",
    "timestamp": "2026-04-11T20:30:00"
  }
}
```

**Response `404`:**
```json
{
  "status": "error",
  "error_code": "CITY_NOT_FOUND",
  "message": "Không tìm thấy dữ liệu thời tiết cho khu vực: 'XYZ'"
}
```

**Response `401`:**
```json
{
  "status": "error",
  "error_code": "API_KEY_INVALID",
  "message": "API Key thời tiết không hợp lệ hoặc chưa được kích hoạt"
}
```

**Response `500`:**
```json
{
  "status": "error",
  "error_code": "NETWORK_ERROR",
  "message": "Máy chủ đang mất kết nối Internet"
}
```

---

## 9️⃣ Gợi Ý Ngữ Cảnh (Context Suggestions)

> Tính năng nâng cao — Backend phân tích dữ liệu cảm biến/thời gian và gợi ý hành động phù hợp.

### `GET /api/context/suggestions` — Lấy Gợi Ý Hiện Tại

**Response `200`:**
```json
{
  "status": "success",
  "data": {
    "context": "hot",
    "reason": "Nhiệt độ phòng đang 32°C, cao hơn ngưỡng thoải mái",
    "suggestions": [
      {
        "pending_id": "pending_001",
        "device_id": 5,
        "device_name": "Quạt Phòng Khách",
        "action": "ON",
        "detail": "Bật quạt tốc độ 3"
      },
      {
        "pending_id": "pending_002",
        "device_id": 6,
        "device_name": "Quạt Phòng Ngủ",
        "action": "ON",
        "detail": "Bật quạt tốc độ 2"
      }
    ],
    "expires_in": 60,
    "timestamp": "2026-04-11T20:30:00"
  }
}
```

> Các giá trị `context`: `"hot"`, `"cold"`, `"dark"`, `"bright"`, `"sleep"`, `"wake"`, `"leave"`, `"arrive"`

---

### `POST /api/context/confirm` — Xác Nhận/Từ Chối Gợi Ý

**Request Body:**
```json
{
  "pending_id": "pending_001",
  "confirm": true
}
```

**Response `200` (confirm = true):**
```json
{
  "status": "success",
  "message": "Đã thực thi gợi ý: Bật Quạt Phòng Khách tốc độ 3",
  "data": {
    "pending_id": "pending_001",
    "executed": true
  }
}
```

**Response `200` (confirm = false):**
```json
{
  "status": "success",
  "message": "Đã bỏ qua gợi ý",
  "data": {
    "pending_id": "pending_001",
    "executed": false,
    "status": "cancelled"
  }
}
```

---

## 🔟 Bảng Mã Lỗi (Error Codes)

| Error Code | HTTP Status | Mô tả |
|------------|-------------|--------|
| `DEVICE_NOT_FOUND` | 404 | Không tìm thấy thiết bị với ID được truyền |
| `INVALID_ROOM` | 404 | Phòng không tồn tại |
| `INVALID_ACTION` | 400 | Lệnh/hành động không hợp lệ (VD: speed=5) |
| `SCHEDULE_NOT_FOUND` | 404 | Không tìm thấy lịch hẹn giờ |
| `ALARM_NOT_FOUND` | 404 | Không tìm thấy báo thức |
| `SENSOR_ERROR` | 404 | Không có dữ liệu cảm biến |
| `CITY_NOT_FOUND` | 404 | Không tìm thấy thành phố |
| `API_KEY_INVALID` | 401 | API key bên thứ 3 không hợp lệ |
| `NETWORK_ERROR` | 500 | Server mất kết nối Internet |
| `MQTT_TIMEOUT` | 504 | Không nhận được phản hồi từ ESP32 |
| `INTERNAL_ERROR` | 500 | Lỗi hệ thống nội bộ |

---

## Phụ Lục A: MQTT Topics (Backend ↔ ESP32)

> Phần này mô tả giao tiếp MQTT **nội bộ** giữa FastAPI Backend và ESP32. Flutter App **KHÔNG** truy cập trực tiếp các topic này.

### A.1. Backend → ESP32 (Gửi Lệnh Điều Khiển)

| Topic | Payload | Mô tả |
|-------|---------|--------|
| `home/control/device/{device_id}` | `"ON"` / `"OFF"` | Bật/tắt đèn, loa, cửa |
| `home/control/device/{device_id}` | `{"speed": 2}` | Điều khiển quạt |
| `home/control/auto/{type}` | `"ON"` / `"OFF"` | Bật/tắt chế độ tự động |

### A.2. ESP32 → Backend (Gửi Dữ Liệu Cảm Biến)

| Topic | Payload | Mô tả |
|-------|---------|--------|
| `home/sensors/9` | `{"temp": 28, "humi": 65}` | DHT11: nhiệt độ + độ ẩm |
| `home/sensors/10` | `{"light": 450}` | Cảm biến ánh sáng |

### A.3. Sơ Đồ Luồng Tổng Hợp

```
┌──────────────┐                          ┌──────────────┐                         ┌──────────────┐
│              │  HTTP REST API            │              │  MQTT                   │              │
│  Flutter App │ ════════════════════════► │  FastAPI     │ ══════════════════════► │    ESP32     │
│              │  POST /api/control/...    │  Backend     │  home/control/device/#  │              │
│              │ ◄════════════════════════ │              │ ◄══════════════════════ │              │
│              │  JSON Response            │              │  home/sensors/#         │              │
└──────────────┘                          └──────┬───────┘                         └──────────────┘
                                                 │
                                                 │ SQLite
                                                 ▼
                                          ┌──────────────┐
                                          │  smarthome2  │
                                          │    .db       │
                                          └──────────────┘
```

---

## Phụ Lục B: Tổng Hợp Endpoint

| # | Method | Endpoint | Nhóm |
|---|--------|----------|------|
| 1 | GET | `/api/health` | Hệ thống |
| 2 | GET | `/api/time` | Hệ thống |
| 3 | POST | `/api/control/light/{device_id}` | Điều khiển |
| 4 | POST | `/api/control/light/all` | Điều khiển |
| 5 | POST | `/api/control/fan/{device_id}` | Điều khiển |
| 6 | POST | `/api/control/fan/{device_id}/adjust` | Điều khiển |
| 7 | POST | `/api/control/door/{device_id}` | Điều khiển |
| 8 | POST | `/api/control/buzzer/{device_id}` | Điều khiển |
| 9 | POST | `/api/control/auto/{type}` | Điều khiển |
| 10 | GET | `/api/status/devices` | Trạng thái |
| 11 | GET | `/api/status/devices/{device_id}` | Trạng thái |
| 12 | GET | `/api/status/rooms/{room_slug}` | Trạng thái |
| 13 | GET | `/api/status/door` | Trạng thái |
| 14 | GET | `/api/sensors/latest/{device_id}` | Cảm biến |
| 15 | GET | `/api/sensors/all` | Cảm biến |
| 16 | GET | `/api/sensors/history/{device_id}` | Cảm biến |
| 17 | POST | `/api/schedules/set` | Hẹn giờ |
| 18 | POST | `/api/schedules/set-timer` | Hẹn giờ |
| 19 | POST | `/api/schedules/batch` | Hẹn giờ |
| 20 | GET | `/api/schedules/active` | Hẹn giờ |
| 21 | DELETE | `/api/schedules/{schedule_id}` | Hẹn giờ |
| 22 | DELETE | `/api/schedules/cancel-all` | Hẹn giờ |
| 23 | POST | `/api/alarms/set` | Báo thức |
| 24 | DELETE | `/api/alarms/{alarm_id}` | Báo thức |
| 25 | GET | `/api/alarms/active` | Báo thức |
| 26 | POST | `/api/bulk/control` | Hàng loạt |
| 27 | POST | `/api/bulk/all` | Hàng loạt |
| 28 | GET | `/api/weather/current` | Thời tiết |
| 29 | GET | `/api/context/suggestions` | Ngữ cảnh |
| 30 | POST | `/api/context/confirm` | Ngữ cảnh |

**Tổng cộng: 30 endpoints**
