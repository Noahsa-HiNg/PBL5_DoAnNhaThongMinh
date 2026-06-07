import asyncio
from datetime import datetime
from core.database import get_db_connection, delete_old_history
from services.mqtt_service import mqtt_service
from core.ws_manager import socketio_manager
import json


async def alarm_worker():
    """Quet bang schedules moi 5 giay, kich hoat lenh den han"""
    print("[Worker] Schedule da bat dau...")
    while True:
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            # JOIN voi bang devices de lay type va name cua thiet bi
            cursor.execute(
                """SELECT s.*, d.type AS device_type, d.name AS device_name
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
                device_name = job['device_name'] or f"Thiet bi {did}"

                if device_type == "fan":
                    # Hardware quat nhan JSON {"speed": 0-3}, KHONG nhan chuoi
                    # "ON"/"OFF" nhu den/buzzer.
                    # command luu trong DB co the la "0"/"1"/"2"/"3" (so)
                    # hoac "on"/"off" (backward-compat).
                    try:
                        speed = int(cmd)
                    except (ValueError, TypeError):
                        speed = 2 if str(cmd).lower() == "on" else 0

                    payload = json.dumps({"speed": speed})
                    mqtt_service.publish_command(did, payload)
                    # Luu DB duoi dang so chuoi "0"/"1"/"2"/"3"
                    conn.execute("UPDATE devices SET status = ? WHERE id = ?", (str(speed), did))
                    await socketio_manager.broadcast_device_update(did, "fan", device_name, {"state": "on", "speed": speed})
                    print(f"[Worker] KICH HOAT (Quat): Thiet bi {did} -> speed={speed}")
                else:
                    # Den / buzzer / cua -> gui chuoi tho "ON"/"OFF"/"LOCK"/...
                    mqtt_service.publish_command(did, cmd.upper())
                    conn.execute("UPDATE devices SET status = ? WHERE id = ?", (cmd.lower(), did))
                    state = "on" if cmd.lower() == "on" else "off"
                    await socketio_manager.broadcast_device_update(did, device_type, device_name, {"state": state})
                    print(f"[Worker] KICH HOAT ({device_type}): Thiet bi {did} -> Lenh: {cmd}")

                conn.execute("UPDATE schedules SET status = 'DONE' WHERE schedule_id = ?", (sid,))

            conn.commit()
            conn.close()
            
        except Exception as e:
            print(f"[Worker] Loi Worker hen gio: {e}")

        await asyncio.sleep(5)


async def cleanup_worker():
    """Moi 24 gio xoa du lieu lich su cu hon 7 ngay"""
    print("[Worker] Don dep du lieu da bat dau...")
    while True:
        delete_old_history()
        await asyncio.sleep(86400)  # 24 gio