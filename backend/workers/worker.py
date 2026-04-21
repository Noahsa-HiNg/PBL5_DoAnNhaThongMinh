import asyncio
from datetime import datetime
from core.database import get_db_connection, delete_old_history
from services.mqtt_service import mqtt_service
import json


async def alarm_worker():
    """Quét bảng schedules mỗi 5 giây, kích hoạt lệnh đến hạn"""
    print("🚀 Worker hẹn giờ (schedule) đã bắt đầu...")
    while True:
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            # JOIN với bảng devices để lấy type của thiết bị
            cursor.execute(
                """SELECT s.*, d.type AS device_type
                   FROM schedules s
                   LEFT JOIN devices d ON s.device_id = d.id
                   WHERE s.status = 'PENDING' AND s.trigger_time <= ?""",
                (current_time,)
            )
            jobs = cursor.fetchall()

            for job in jobs:
                sid         = job['schedule_id']
                did         = job['device_id']
                cmd         = job['command']
                device_type = job['device_type']

                if device_type == "fan":
                    # ──────────────────────────────────────────────────────────
                    # Hardware quạt nhận JSON {"speed": 0-3}, KHÔNG nhận chuỗi
                    # "ON"/"OFF" như đèn/buzzer.
                    # command lưu trong DB có thể là "0"/"1"/"2"/"3" (số)
                    # hoặc "on"/"off" (backward-compat).
                    # ──────────────────────────────────────────────────────────
                    try:
                        speed = int(cmd)
                    except (ValueError, TypeError):
                        speed = 2 if str(cmd).lower() == "on" else 0

                    payload = json.dumps({"speed": speed})
                    mqtt_service.publish_command(did, payload)
                    # Lưu DB dưới dạng số chuỗi "0"/"1"/"2"/"3"
                    conn.execute("UPDATE devices SET status = ? WHERE id = ?", (str(speed), did))
                    print(f"⏰ KÍCH HOẠT (Quạt): Thiết bị {did} → speed={speed}")
                else:
                    # Đèn / buzzer / cửa → gửi chuỗi thô "ON"/"OFF"/"LOCK"/...
                    mqtt_service.publish_command(did, cmd.upper())
                    conn.execute("UPDATE devices SET status = ? WHERE id = ?", (cmd.lower(), did))
                    print(f"⏰ KÍCH HOẠT ({device_type}): Thiết bị {did} → Lệnh: {cmd}")

                conn.execute("UPDATE schedules SET status = 'DONE' WHERE schedule_id = ?", (sid,))

            conn.commit()
            conn.close()
            
        except Exception as e:
            print(f"❌ Lỗi Worker hẹn giờ: {e}")

        await asyncio.sleep(5)


async def buzzer_alarm_worker():
    """Quét bảng alarms mỗi 30 giây, kích hoạt buzzer khi đến giờ báo thức"""
    print("🚀 Worker báo thức (alarm) đã bắt đầu...")
    while True:
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            current_time = datetime.now().strftime("%H:%M")
            cursor.execute(
                "SELECT * FROM alarms WHERE status = 'active' AND time = ?",
                (current_time,)
            )
            alarms = cursor.fetchall()
            
            for alarm in alarms:
                # ── Bật buzzer (device_id = 12) qua publish_command chuẩn ──
                mqtt_service.publish_command(12, "ON")
                # Cập nhật trạng thái buzzer trong DB
                conn.execute("UPDATE devices SET status = 'on' WHERE id = 12")
                print(f"🔔 BÁO THỨC: {alarm['label'] or alarm['alarm_id']} lúc {alarm['time']}")

                # ── Tự động tắt buzzer sau 60 giây ──
                async def _auto_off():
                    await asyncio.sleep(60)
                    mqtt_service.publish_command(12, "OFF")
                    try:
                        _c = get_db_connection()
                        _c.execute("UPDATE devices SET status = 'off' WHERE id = 12")
                        _c.commit()
                        _c.close()
                    except Exception as e_off:
                        print(f"⚠️ Không cập nhật được DB khi tắt buzzer: {e_off}")
                    print("🔕 Đã tắt buzzer sau 60 giây")

                asyncio.create_task(_auto_off())

                # Nếu không repeat → đánh dấu done
                if not alarm["repeat"]:
                    conn.execute(
                        "UPDATE alarms SET status = 'done' WHERE alarm_id = ?",
                        (alarm["alarm_id"],)
                    )
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            print(f"❌ Lỗi Worker báo thức: {e}")
        
        await asyncio.sleep(30)


async def cleanup_worker():
    """Mỗi 24 giờ xóa dữ liệu lịch sử cũ hơn 7 ngày"""
    print("🚀 Worker dọn dẹp dữ liệu đã bắt đầu...")
    while True:
        delete_old_history()
        await asyncio.sleep(86400)  # 24 giờ