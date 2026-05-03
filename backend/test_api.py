"""
╔══════════════════════════════════════════════════════════════════╗
║        PBL5 Smart Home — Kiểm thử toàn bộ API Backend           ║
║   Chạy lệnh: python test_api.py                                  ║
╚══════════════════════════════════════════════════════════════════╝

Yêu cầu: pip install requests
Server phải đang chạy tại http://localhost:8000
"""

import requests
import json
import time
from datetime import datetime, timedelta

BASE_URL = "http://localhost:8000"

# ─── Màu sắc terminal ────────────────────────────────────────────
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

# ─── Biến thống kê ───────────────────────────────────────────────
passed = 0
failed = 0
skipped = 0
results = []

def print_header(title: str):
    print(f"\n{BOLD}{CYAN}{'═'*60}{RESET}")
    print(f"{BOLD}{CYAN}  {title}{RESET}")
    print(f"{BOLD}{CYAN}{'═'*60}{RESET}")

def test(method: str, path: str, desc: str,
         body=None, params=None,
         expect_status=200, expect_key=None, skip=False):
    global passed, failed, skipped

    if skip:
        skipped += 1
        print(f"  {YELLOW}⏭  SKIP{RESET}  {desc}")
        results.append({"test": desc, "result": "SKIP", "status": None})
        return None

    url = BASE_URL + path
    try:
        r = getattr(requests, method.lower())(
            url,
            json=body,
            params=params,
            timeout=10
        )
        ok = r.status_code == expect_status
        if ok and expect_key:
            ok = expect_key in r.json()

        if ok:
            passed += 1
            print(f"  {GREEN}✔  PASS{RESET}  [{r.status_code}] {desc}")
            results.append({"test": desc, "result": "PASS", "status": r.status_code})
        else:
            failed += 1
            print(f"  {RED}✘  FAIL{RESET}  [{r.status_code}] {desc}")
            try:
                print(f"         ↳ Body: {json.dumps(r.json(), ensure_ascii=False)[:200]}")
            except Exception:
                print(f"         ↳ Body: {r.text[:200]}")
            results.append({"test": desc, "result": "FAIL", "status": r.status_code})

        return r
    except requests.exceptions.ConnectionError:
        failed += 1
        print(f"  {RED}✘  FAIL{RESET}  [CONNECTION_ERROR] {desc}")
        print(f"         ↳ Không kết nối được server tại {BASE_URL}")
        results.append({"test": desc, "result": "FAIL", "status": "CONNECTION_ERROR"})
        return None
    except Exception as e:
        failed += 1
        print(f"  {RED}✘  FAIL{RESET}  [EXCEPTION] {desc}")
        print(f"         ↳ {e}")
        results.append({"test": desc, "result": "FAIL", "status": "EXCEPTION"})
        return None


# ════════════════════════════════════════════════════════════════
# 1. HỆ THỐNG (System)
# ════════════════════════════════════════════════════════════════
print_header("1. HỆ THỐNG")

test("GET", "/",          "Root — server đang sống",        expect_key="message")
test("GET", "/api/health","Health check + MQTT status",     expect_key="data")
test("GET", "/api/time",  "Lấy giờ + ngữ cảnh thời gian",  expect_key="time")

# ════════════════════════════════════════════════════════════════
# 2. TRẠNG THÁI THIẾT BỊ (Status)
# ════════════════════════════════════════════════════════════════
print_header("2. TRẠNG THÁI THIẾT BỊ")

test("GET", "/api/status/devices",         "Lấy danh sách TẤT CẢ thiết bị",      expect_key="data")
test("GET", "/api/status/devices/1",       "Trạng thái đèn #1",                   expect_key="data")
test("GET", "/api/status/devices/5",       "Trạng thái quạt #5",                  expect_key="data")
test("GET", "/api/status/devices/9",       "Trạng thái cảm biến DHT11 #9",        expect_key="data")
test("GET", "/api/status/devices/11",      "Trạng thái khóa cửa #11",             expect_key="data")
test("GET", "/api/status/devices/12",      "Trạng thái loa #12",                  expect_key="data")
test("GET", "/api/status/devices/999",     "Device không tồn tại → 404",          expect_status=404)
test("GET", "/api/status/door",            "Trạng thái cửa chính (dedicated)",    expect_key="data")
test("GET", "/api/status/rooms/living_room", "Thiết bị phòng khách",              expect_key="data")
test("GET", "/api/status/rooms/bedroom",   "Thiết bị phòng ngủ",                  expect_key="data")
test("GET", "/api/status/rooms/kitchen",   "Thiết bị nhà bếp",                    expect_key="data")
test("GET", "/api/status/rooms/xxx",       "Phòng không tồn tại → 404",           expect_status=404)

# ════════════════════════════════════════════════════════════════
# 3. CẢM BIẾN (Sensor)
# ════════════════════════════════════════════════════════════════
print_header("3. CẢM BIẾN")

test("GET", "/api/sensors/all",            "Tất cả cảm biến (DHT11 + Ánh sáng)", expect_key="data")
test("GET", "/api/sensors/latest/9",       "Cảm biến DHT11 mới nhất",            expect_key="data")
test("GET", "/api/sensors/latest/10",      "Cảm biến ánh sáng mới nhất",         expect_key="data")
test("GET", "/api/sensors/latest/1",       "Device #1 không phải sensor → 404",  expect_status=404)
test("GET", "/api/sensors/history/9",      "Lịch sử DHT11 (mặc định 50)",        expect_key="data")
test("GET", "/api/sensors/history/9",      "Lịch sử DHT11 giới hạn 10",          params={"limit": 10}, expect_key="data")
test("GET", "/api/sensors/history/10",     "Lịch sử ánh sáng",                   expect_key="data")

# ════════════════════════════════════════════════════════════════
# 4. ĐIỀU KHIỂN ĐÈN (Light Control)
# ════════════════════════════════════════════════════════════════
print_header("4. ĐIỀU KHIỂN ĐÈN")

test("POST", "/api/control/light/1",  "Bật đèn #1",          body={"state": "ON"},  expect_key="data")
test("POST", "/api/control/light/1",  "Tắt đèn #1",          body={"state": "OFF"}, expect_key="data")
test("POST", "/api/control/light/2",  "Bật đèn #2",          body={"state": "ON"},  expect_key="data")
test("POST", "/api/control/light/3",  "Bật đèn #3",          body={"state": "ON"},  expect_key="data")
test("POST", "/api/control/light/4",  "Bật đèn #4",          body={"state": "ON"},  expect_key="data")
test("POST", "/api/control/light/all","Bật TẤT CẢ đèn",      body={"state": "ON"},  expect_key="data")
test("POST", "/api/control/light/all","Tắt TẤT CẢ đèn",      body={"state": "OFF"}, expect_key="data")
test("POST", "/api/control/light/1",  "Lệnh đèn không hợp lệ → 400",
     body={"state": "BLINK"}, expect_status=400)
test("POST", "/api/control/light/999","Đèn không tồn tại → 404",
     body={"state": "ON"}, expect_status=404)

# ════════════════════════════════════════════════════════════════
# 5. ĐIỀU KHIỂN QUẠT (Fan Control)
# ════════════════════════════════════════════════════════════════
print_header("5. ĐIỀU KHIỂN QUẠT")

test("POST", "/api/control/fan/5",  "Bật quạt #5 tốc độ 2", body={"state": "on", "speed": 2}, expect_key="data")
test("POST", "/api/control/fan/5",  "Bật quạt #5 tốc độ 3", body={"state": "on", "speed": 3}, expect_key="data")
test("POST", "/api/control/fan/5",  "Tắt quạt #5",           body={"state": "off"},            expect_key="data")
test("POST", "/api/control/fan/5",  "Bật quạt không có speed (mặc định 2)", body={"state": "on"}, expect_key="data")
test("POST", "/api/control/fan/5/adjust", "Tăng tốc quạt #5",  body={"action": "up"},   expect_key="data")
test("POST", "/api/control/fan/5/adjust", "Giảm tốc quạt #5",  body={"action": "down"}, expect_key="data")
test("POST", "/api/control/fan/5",  "Tốc độ quạt không hợp lệ → 400",
     body={"state": "on", "speed": 5}, expect_status=400)
test("POST", "/api/control/fan/999","Quạt không tồn tại → 404",
     body={"state": "on"}, expect_status=404)

# ════════════════════════════════════════════════════════════════
# 6. ĐIỀU KHIỂN KHÓA CỬA (Door)
# ════════════════════════════════════════════════════════════════
print_header("6. ĐIỀU KHIỂN KHÓA CỬA")

test("POST", "/api/control/door/11",  "Mở cửa chính",    body={"action": "unlock"}, expect_key="data")
test("POST", "/api/control/door/11",  "Khóa cửa chính",  body={"action": "lock"},   expect_key="data")
test("POST", "/api/control/door/11",  "Lệnh cửa sai → 400",
     body={"action": "open"}, expect_status=400)
test("POST", "/api/control/door/999", "Cửa không tồn tại → 404",
     body={"action": "lock"}, expect_status=404)

# ════════════════════════════════════════════════════════════════
# 7. ĐIỀU KHIỂN LOA (Buzzer)
# ════════════════════════════════════════════════════════════════
print_header("7. ĐIỀU KHIỂN LOA / BUZZER")

test("POST", "/api/control/buzzer/12", "Bật loa #12",     body={"state": "on"},  expect_key="data")
test("POST", "/api/control/buzzer/12", "Tắt loa #12",     body={"state": "off"}, expect_key="data")
test("POST", "/api/control/buzzer/12", "Lệnh loa sai → 400",
     body={"state": "beep"}, expect_status=400)
test("POST", "/api/control/buzzer/999","Loa không tồn tại → 404",
     body={"state": "on"}, expect_status=404)

# ════════════════════════════════════════════════════════════════
# 8. CHẾ ĐỘ TỰ ĐỘNG (Auto Mode)
# ════════════════════════════════════════════════════════════════
print_header("8. CHẾ ĐỘ TỰ ĐỘNG")

test("POST", "/api/control/auto/light", "Bật auto đèn",     body={"command": "ON"},  expect_key="data")
test("POST", "/api/control/auto/light", "Tắt auto đèn",     body={"command": "OFF"}, expect_key="data")
test("POST", "/api/control/auto/fan",   "Bật auto quạt",    body={"command": "ON"},  expect_key="data")
test("POST", "/api/control/auto/all",   "Bật auto tất cả",  body={"command": "ON"},  expect_key="data")
test("POST", "/api/control/auto/light", "Lệnh auto sai → 400",
     body={"command": "MAYBE"}, expect_status=400)

# ════════════════════════════════════════════════════════════════
# 9. HẸN GIỜ / LỊCH TRÌNH (Schedules)
# ════════════════════════════════════════════════════════════════
print_header("9. HẸN GIỜ / LỊCH TRÌNH")

future_time = (datetime.now() + timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S")

r_sched = test("POST", "/api/schedules/set",
    "Đặt hẹn giờ tuyệt đối cho đèn #1",
    body={"device_id": 1, "command": "ON", "time": future_time},
    expect_key="data"
)
schedule_id = None
if r_sched and r_sched.status_code == 200:
    schedule_id = r_sched.json().get("data", {}).get("schedule_id")

test("POST", "/api/schedules/set-timer",
    "Hẹn giờ sau 5 phút cho quạt #5",
    body={"device_id": 5, "command": "ON", "delay_minutes": 5},
    expect_key="data"
)
test("POST", "/api/schedules/batch",
    "Hẹn giờ hàng loạt tắt đèn sau 10 phút",
    body={"device_type": "light", "command": "OFF", "delay_minutes": 10},
    expect_key="data"
)
test("GET", "/api/schedules/active",
    "Lấy danh sách hẹn giờ đang PENDING",
    expect_key="data"
)

# Hủy lịch vừa tạo (nếu có)
if schedule_id:
    test("DELETE", f"/api/schedules/{schedule_id}",
         f"Hủy hẹn giờ #{schedule_id}",
         expect_key=None, expect_status=200
    )
test("DELETE", "/api/schedules/99999",
    "Hủy hẹn giờ không tồn tại → 404",
    expect_status=404
)
test("DELETE", "/api/schedules/cancel-all",
    "Hủy TẤT CẢ hẹn giờ đang PENDING",
    expect_key="data"
)

# ════════════════════════════════════════════════════════════════
# 10. BÁO THỨC (Alarm)
# ════════════════════════════════════════════════════════════════
print_header("10. BÁO THỨC")

r_alarm = test("POST", "/api/alarms/set",
    "Đặt báo thức 07:30 (không lặp)",
    body={"time": "07:30", "repeat": False, "label": "Dậy sớm"},
    expect_key="data"
)
alarm_id = None
if r_alarm and r_alarm.status_code == 200:
    alarm_id = r_alarm.json().get("data", {}).get("alarm_id")

test("POST", "/api/alarms/set",
    "Đặt báo thức 22:00 (lặp lại)",
    body={"time": "22:00", "repeat": True, "label": "Giờ ngủ"},
    expect_key="data"
)
test("POST", "/api/alarms/set",
    "Thời gian không hợp lệ → 400",
    body={"time": "25:99", "repeat": False},
    expect_status=400
)
test("GET", "/api/alarms/active",
    "Lấy danh sách báo thức đang bật",
    expect_key="data"
)

if alarm_id:
    test("DELETE", f"/api/alarms/{alarm_id}",
         f"Hủy báo thức {alarm_id}",
         expect_status=200
    )
test("DELETE", "/api/alarms/alarm_fakeid",
    "Hủy báo thức không tồn tại → 404",
    expect_status=404
)

# ════════════════════════════════════════════════════════════════
# 11. ĐIỀU KHIỂN HÀNG LOẠT (Bulk)
# ════════════════════════════════════════════════════════════════
print_header("11. ĐIỀU KHIỂN HÀNG LOẠT")

test("POST", "/api/bulk/control",
    "Bulk: bật đèn #1, tắt quạt #5",
    body={
        "actions": [
            {"device_id": 1, "command": "ON"},
            {"device_id": 5, "command": "0"}
        ]
    },
    expect_key="data"
)
test("POST", "/api/bulk/control",
    "Bulk: device không tồn tại (partial failure)",
    body={
        "actions": [
            {"device_id": 1,   "command": "ON"},
            {"device_id": 999, "command": "ON"}
        ]
    },
    expect_key="data"
)
test("POST", "/api/bulk/all",
    "Bulk: tắt TẤT CẢ thiết bị",
    body={"state": "OFF"},
    expect_key="data"
)
test("POST", "/api/bulk/all",
    "Bulk: bật TẤT CẢ thiết bị",
    body={"state": "ON"},
    expect_key="data"
)
test("POST", "/api/bulk/all",
    "Bulk: state không hợp lệ → 400",
    body={"state": "TOGGLE"},
    expect_status=400
)

# ════════════════════════════════════════════════════════════════
# 12. THỜI TIẾT (Weather)
# ════════════════════════════════════════════════════════════════
print_header("12. THỜI TIẾT")

test("GET", "/api/weather/current",
    "Thời tiết Đà Nẵng (default city)",
    expect_key="data"
)
test("GET", "/api/weather/current",
    "Thời tiết tùy chọn — Hà Nội",
    params={"city": "Hanoi"},
    expect_key="data"
)
test("GET", "/api/weather/current",
    "Thành phố không tồn tại → 404",
    params={"city": "xxxcitynotfound999"},
    expect_status=404
)

# ════════════════════════════════════════════════════════════════
# 13. NGỮ CẢNH / GỢI Ý (Context)
# ════════════════════════════════════════════════════════════════
print_header("13. NGỮ CẢNH / GỢI Ý")

r_ctx = test("GET", "/api/context/suggestions",
    "Lấy gợi ý dựa trên cảm biến + giờ hiện tại",
    expect_key="data"
)

# Thử confirm nếu có gợi ý
if r_ctx and r_ctx.status_code == 200:
    suggestions = r_ctx.json().get("data", {}).get("suggestions", [])
    if suggestions:
        pid = suggestions[0]["pending_id"]
        test("POST", "/api/context/confirm",
             f"Xác nhận gợi ý {pid}",
             body={"pending_id": pid, "confirm": True},
             expect_key="data"
        )
    else:
        print(f"  {YELLOW}ℹ  INFO   Không có gợi ý nào (điều kiện chưa thỏa){RESET}")
        skipped += 1

test("POST", "/api/context/confirm",
    "Confirm pending_id không tồn tại → 404",
    body={"pending_id": "pending_invalid", "confirm": True},
    expect_status=404
)

# ════════════════════════════════════════════════════════════════
# KẾT QUẢ TỔNG HỢP
# ════════════════════════════════════════════════════════════════
total = passed + failed + skipped
print(f"\n{BOLD}{'═'*60}{RESET}")
print(f"{BOLD}  KẾT QUẢ KIỂM THỬ — PBL5 Smart Home API{RESET}")
print(f"{'═'*60}")
print(f"  Tổng số test : {total}")
print(f"  {GREEN}✔ Passed{RESET}      : {passed}")
print(f"  {RED}✘ Failed{RESET}      : {failed}")
print(f"  {YELLOW}⏭ Skipped{RESET}     : {skipped}")
rate = (passed / (passed + failed) * 100) if (passed + failed) > 0 else 0
print(f"  Tỉ lệ pass   : {rate:.1f}%")
print(f"{'═'*60}\n")

if failed > 0:
    print(f"{RED}{BOLD}  ⚠ Các test FAIL:{RESET}")
    for r in results:
        if r["result"] == "FAIL":
            print(f"  {RED}  • {r['test']}  [{r['status']}]{RESET}")
    print()
