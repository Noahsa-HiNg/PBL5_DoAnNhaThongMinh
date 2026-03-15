import sqlite3
from models.schemas import DeviceTypeBase, DeviceTypeResponse

DB_NAME = "smarthome.db"

class DeviceTypeRepo:
    def get_all_device_types(self):
        conn = sqlite3.connect(DB_NAME)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM device_types")
        rows = cursor.fetchall()
        conn.close()
        return [DeviceTypeResponse(**row) for row in rows]

    def get_device_type_by_id(self, type_id: int):
        conn = sqlite3.connect(DB_NAME)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM device_types WHERE id = ?", (type_id,))
        row = cursor.fetchone()
        conn.close()
        return DeviceTypeResponse(**row) if row else None

    def get_device_type_by_name(self, type_name: str):
        conn = sqlite3.connect(DB_NAME)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM device_types WHERE type_name = ?", (type_name,))
        row = cursor.fetchone()
        conn.close()
        return DeviceTypeResponse(**row) if row else None

    def get_device_type_by_category(self, category: str):
        conn = sqlite3.connect(DB_NAME)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM device_types WHERE category = ?", (category,))
        rows = cursor.fetchall()
        conn.close()
        return [DeviceTypeResponse(**row) for row in rows]
