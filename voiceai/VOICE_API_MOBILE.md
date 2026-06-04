# API Giao tiếp giọng nói / văn bản — Tài liệu dành cho Mobile

**Base URL:** `http://<IP_SERVER>:8000`  
**Content-Type:** `application/json`

---

## Endpoint: Gửi tin nhắn văn bản

### `POST /api/voice/message`

Gửi một đoạn văn bản từ người dùng lên server. Server sẽ chuyển tiếp sang model xử lý ngôn ngữ (NLP), sau đó trả về phản hồi dạng text cho mobile.

---

### Request

**Header:**
```
Content-Type: application/json
```

**Body (JSON):**
```json
{
  "message": "Bật đèn phòng khách"
}
```

| Field     | Kiểu   | Bắt buộc | Mô tả                        |
|-----------|--------|----------|------------------------------|
| `message` | string | ✅ Có    | Nội dung văn bản người dùng nhập vào |

---

### Response — Thành công (`200 OK`)

```json
{
  "status": "success",
  "user_text": "Bật đèn phòng khách",
  "system_response": "Đã bật đèn phòng khách thành công."
}
```

| Field             | Kiểu   | Mô tả                                              |
|-------------------|--------|----------------------------------------------------|
| `status`          | string | `"success"` nếu xử lý thành công                  |
| `user_text`       | string | Văn bản gốc mà người dùng đã gửi lên              |
| `system_response` | string | **Phản hồi từ model xử lý ngôn ngữ** — hiển thị cho người dùng |

> `system_response` là đoạn text bạn cần hiển thị lên giao diện chat.

---

### Response — Lỗi

**`400 Bad Request`** — Tin nhắn rỗng:
```json
{
  "detail": "Nội dung tin nhắn không được để trống."
}
```

**`500 Internal Server Error`** — Server hoặc model xử lý gặp sự cố:
```json
{
  "detail": "Lỗi kết nối đến NLP server: ..."
}
```

**`504 Gateway Timeout`** — Model xử lý quá lâu (> 30 giây):
```json
{
  "detail": "Hệ thống xử lý quá lâu, vui lòng thử lại."
}
```

---

### Ví dụ gọi API

**cURL:**
```bash
curl -X POST http://192.168.1.100:8000/api/voice/message \
  -H "Content-Type: application/json" \
  -d '{"message": "Bật đèn phòng khách"}'
```

**Dart / Flutter:**
```dart
import 'dart:convert';
import 'package:http/http.dart' as http;

Future<String> sendMessage(String userText) async {
  final url = Uri.parse('http://192.168.1.100:8000/api/voice/message');

  final response = await http.post(
    url,
    headers: {'Content-Type': 'application/json'},
    body: jsonEncode({'message': userText}),
  );

  if (response.statusCode == 200) {
    final data = jsonDecode(response.body);
    return data['system_response']; // ← đây là text cần hiển thị
  } else {
    throw Exception('Lỗi: ${response.body}');
  }
}
```

---

## Endpoint: Lấy lịch sử hội thoại

### `GET /api/voice/conversations`

Trả về toàn bộ lịch sử tin nhắn giữa người dùng và hệ thống, dùng để render màn hình chat.

**Query Params (tuỳ chọn):**

| Param   | Kiểu | Mặc định | Mô tả                            |
|---------|------|----------|----------------------------------|
| `limit` | int  | `100`    | Số lượng tin nhắn tối đa trả về  |

**Ví dụ:** `GET /api/voice/conversations?limit=50`

---

### Response (`200 OK`)

```json
{
  "status": "success",
  "data": [
    {
      "id": 1,
      "sender": "user",
      "message": "Bật đèn phòng khách",
      "timestamp": "2026-05-04 00:01:00"
    },
    {
      "id": 2,
      "sender": "system",
      "message": "Đã bật đèn phòng khách thành công.",
      "timestamp": "2026-05-04 00:01:02"
    }
  ]
}
```

| Field       | Kiểu   | Mô tả                                      |
|-------------|--------|--------------------------------------------|
| `id`        | int    | ID tự tăng của tin nhắn                    |
| `sender`    | string | `"user"` — người dùng, `"system"` — hệ thống |
| `message`   | string | Nội dung tin nhắn                          |
| `timestamp` | string | Thời gian gửi (định dạng `YYYY-MM-DD HH:MM:SS`) |

> **Hiển thị UI:** Nếu `sender == "user"` → hiển thị bên phải (bubble xanh). Nếu `sender == "system"` → hiển thị bên trái (bubble xám).

---

## Luồng hoạt động tổng quan

```
[Mobile] ──POST /api/voice/message──► [FastAPI Server]
                                              │
                                    giữ kết nối, gọi NLP model
                                              │
                                       [NLP Model Server]
                                              │ xử lý lệnh
                                              │ điều khiển thiết bị
                                              │ trả về text phản hồi
                                              │
[Mobile] ◄──── system_response ─────── [FastAPI Server]
                                     (lưu cả 2 tin vào DB)
```

- ⏱ **Thời gian chờ tối đa:** ~30 giây
- 📦 **Dữ liệu lưu DB:** Mỗi lượt chat sẽ lưu 2 bản ghi: 1 của `user` + 1 của `system`
- 🔁 **Lấy lại lịch sử:** Gọi `GET /api/voice/conversations` sau khi mở app để load lại chat cũ
