import asyncio
from datetime import datetime
from database import get_db_connection,delete_old_history
from mqtt_clients import mqtt_service
async def alarm_worker():
    print("🚀 Hệ thống lính gác báo thức đã bắt đầu...")
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
            print(f"❌ Lỗi Worker: {e}")

        await asyncio.sleep(5)


async def cleanup_worker():
    """Hàng ngày sẽ kiểm tra và xóa dữ liệu cũ một lần (Bản Async)"""
    print("🚀 Worker dọn dẹp dữ liệu (Async) đã bắt đầu...")
    while True:
        # 1. Thực hiện dọn dẹp
        delete_old_history()
        
        # 2. Ngủ trong 24 giờ (86400 giây) mà không làm nghẽn Server
        await asyncio.sleep(86400)
def start_cleanup_thread():
    """Hàm để gọi từ main.py"""
    t = threading.Thread(target=cleanup_worker, daemon=True)
    t.start()