import sqlite3
from models.schemas import EspNodeBase, EspNodeResponse

DB_NAME = "smarthome.db"

class EspNodeRepo:
    def get_all_esp_nodes(self):
        conn = sqlite3.connect(DB_NAME)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM esp_nodes")
        rows = cursor.fetchall()
        conn.close()
        return [EspNodeResponse(**row) for row in rows]
    def create_esp_node(self, esp_node: EspNodeBase):
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO esp_nodes (mac_address, location_desc) VALUES (?,?)", (esp_node.mac_address, esp_node.location_desc))
            conn.commit()
            return {"message": "Tạo ESP Node thành công!"}
        except sqlite3.IntegrityError:
            return {"error": "Địa chỉ MAC này đã tồn tại!"}
        finally:
            conn.close()
    def delete_esp_node(self, esp_node_id: int):
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM esp_nodes WHERE id=?", (esp_node_id,))
        conn.commit()
        conn.close()
        return {"message": "Xóa ESP Node thành công!"}
    def update_esp_node(self, esp_node_id: int, esp_node: EspNodeBase):
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        try:
            cursor.execute("UPDATE esp_nodes SET mac_address=?, location_desc=? WHERE id=?", (esp_node.mac_address, esp_node.location_desc, esp_node_id))
            conn.commit()
            return {"message": "Cập nhật ESP Node thành công!"}
        except sqlite3.IntegrityError:
            return {"error": "Địa chỉ MAC này đã tồn tại!"}
        finally:
            conn.close()