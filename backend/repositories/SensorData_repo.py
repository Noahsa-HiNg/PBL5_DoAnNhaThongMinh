import sqlite3
from models.schemas import SensorDataInput, SensorHistoryResponse
from datetime import datetime

DB_NAME = "smarthome.db"

class SensorDataRepo:
    def add_sensor_data(self, data: SensorDataInput):
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # Kiểm tra xem device_id có phải là sensor không
        cursor.execute("""
            SELECT d.id FROM devices d 
            JOIN device_types dt ON d.type_id = dt.id 
            WHERE d.id = ? AND dt.category = 'sensor'
        """, (data.device_id,))
        if not cursor.fetchone():
            conn.close()
            return {"error": "Thiết bị không tồn tại hoặc không phải là cảm biến!"}
            
        cursor.execute("INSERT INTO sensor_history (device_id, value) VALUES (?, ?)", (data.device_id, data.value))
        conn.commit()
        conn.close()
        return {"message": "Đã lưu dữ liệu cảm biến thành công"}

    def get_sensor_history(self, device_id: int = None, limit: int = 50):
        conn = sqlite3.connect(DB_NAME)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = "SELECT * FROM sensor_history"
        params = []
        
        if device_id is not None:
            query += " WHERE device_id = ?"
            params.append(device_id)
            
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, tuple(params))
        rows = cursor.fetchall()
        conn.close()
        
        return [SensorHistoryResponse(**row) for row in rows]
