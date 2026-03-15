import sqlite3
from models.schemas import DeviceCreate,DeviceResponse,DeviceDetailResponse,DeviceUpdate,DeviceStatusResponse

DB_NAME = "smarthome.db"

class DeviceRepo:
    def get_all_devices(self):
        conn = sqlite3.connect(DB_NAME)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM devices")
        rows = cursor.fetchall()
        conn.close()
        return [DeviceResponse(**row) for row in rows]
    def create_device(self, device: DeviceCreate):
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO devices (name, room_id, type_id, esp_id, pin) VALUES (?,?,?,?,?)", (device.name, device.room_id, device.type_id, device.esp_id, device.pin))
            conn.commit()
            return {"message": "Tạo thiết bị thành công!"}
        except sqlite3.IntegrityError:
            return {"error": "Thiết bị này đã tồn tại!"}
        finally:
            conn.close()
    def get_device_by_id(self, device_id: int):
        conn = sqlite3.connect(DB_NAME)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM devices WHERE id=?", (device_id,))
        row = cursor.fetchone()
        conn.close()
        return DeviceResponse(**row) if row else None
    def delete_device(self, device_id: int):
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM devices WHERE id=?", (device_id,))
        conn.commit()
        conn.close()
        return {"message": "Xóa thiết bị thành công!"}
    def update_device(self, device_id: int, device: DeviceUpdate):
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        try:
            cursor.execute("UPDATE devices SET name=?, room_id=?, type_id=?, esp_id=?, pin=? WHERE id=?", (device.name, device.room_id, device.type_id, device.esp_id, device.pin, device_id))
            conn.commit()
            return {"message": "Cập nhật thiết bị thành công!"}
        except sqlite3.IntegrityError:
            return {"error": "Thiết bị này đã tồn tại!"}
        finally:
            conn.close()
    
    def get_device_status(self, device_id: int):
        conn = sqlite3.connect(DB_NAME)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM device_status WHERE device_id=?", (device_id,))
        row = cursor.fetchone()
        conn.close()
        return DeviceStatusResponse(**row) if row else None

    def update_device_status(self, device_id: int, status: str):
        from datetime import datetime
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # Kiểm tra xem thiết bị có tồn tại không đã
        cursor.execute("SELECT id FROM devices WHERE id=?", (device_id,))
        if not cursor.fetchone():
            conn.close()
            return {"error": "Thiết bị không tồn tại!"}

        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Upsert: Nếu chưa có dòng status cho device này thì insert, có rồi thì update
        cursor.execute('''
            INSERT INTO device_status (device_id, status, last_changed) 
            VALUES (?, ?, ?)
            ON CONFLICT(device_id) DO UPDATE SET 
            status=excluded.status, 
            last_changed=excluded.last_changed
        ''', (device_id, status, current_time))
        
        conn.commit()
        conn.close()
        return {"message": "Cập nhật Database thành công!"}
