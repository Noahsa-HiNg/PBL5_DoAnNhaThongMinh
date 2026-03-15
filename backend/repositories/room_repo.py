import sqlite3
from models.schemas import RoomResponse, RoomBase

DB_NAME = "smarthome.db"

class RoomRepo:
    def get_all_rooms(self):
        conn = sqlite3.connect(DB_NAME)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM rooms")
        rows = cursor.fetchall()
        conn.close()
        return [RoomResponse(**row) for row in rows]

    def create_room(self, room: RoomBase):
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO rooms (name) VALUES (?)", (room.name,))
            conn.commit()
            return {"message": "Tạo phòng thành công!"}
        except sqlite3.IntegrityError:
            return {"error": "Tên phòng này đã tồn tại!"}
        finally:
            conn.close()

    def delete_room(self, room_id: int):
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM rooms WHERE id=?", (room_id,))
        conn.commit()
        conn.close()
        return {"message": "Room deleted successfully"}
    
    def update_room(self, room_id: int, room: RoomBase):
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        try:
            cursor.execute("UPDATE rooms SET name=? WHERE id=?", (room.name, room_id))
            conn.commit()
            return {"message": "Room updated successfully"}
        except sqlite3.IntegrityError:
            return {"error": "Tên phòng này đã tồn tại!"}
        finally:
            conn.close()