import asyncio
from datetime import datetime
from core.database import get_db_connection, delete_old_history
from services.mqtt_service import mqtt_service

async def alarm_worker():
    """Quét bảng schedules mỗi 5 giây, kích hoạt lệnh đến hạn"""
    print("🚀 Worker hẹn giờ (schedule) đã bắt đầu...")
    while True:
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute(
                "SELECT * FROM schedules WHERE status = 'PENDING' AND trigger_time <= ?", 
                (current_time,)
            )
            jobs = cursor.fetchall()

            for job in jobs:
                sid = job['schedule_id']
                did = job['device_id']
                cmd = job['command']

                topic = f"home/control/device/{did}"
                mqtt_service.client.publish(topic, cmd)
                print(f"⏰ KÍCH HOẠT: Thiết bị {did} -> Lệnh: {cmd}")

                conn.execute("UPDATE schedules SET status = 'DONE' WHERE schedule_id = ?", (sid,))
                conn.execute("UPDATE devices SET status = ? WHERE id = ?", (cmd, did))

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
                # Kích hoạt buzzer (device_id = 12)
                mqtt_service.client.publish("home/control/device/12", "ON")
                print(f"🔔 BÁO THỨC: {alarm['label'] or alarm['alarm_id']} lúc {alarm['time']}")
                
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