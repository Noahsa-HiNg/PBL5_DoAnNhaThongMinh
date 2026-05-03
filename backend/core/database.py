import sqlite3
import os
from datetime import datetime
from core.config import DB_NAME as _DB_NAME

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, _DB_NAME)

def get_db_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row 
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. BẢNG PHÒNG
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS rooms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            slug TEXT NOT NULL UNIQUE
        )
    ''')
    
    # 2. BẢNG THIẾT BỊ (Đã sửa lại schema chuẩn)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS devices (
            id INTEGER PRIMARY KEY,
            room_id INTEGER,
            name TEXT,
            type TEXT, 
            pin INTEGER,
            status TEXT,
            FOREIGN KEY (room_id) REFERENCES rooms (id)
        )
    ''')

    # 3. BẢNG LỊCH SỬ
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS device_history (
            log_id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id INTEGER,
            status TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 4. BẢNG HẸN GIỜ (SCHEDULES)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS schedules (
            schedule_id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id INTEGER,
            command TEXT,           
            trigger_time DATETIME,  
            status TEXT DEFAULT 'PENDING', 
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS alarms (
            alarm_id TEXT PRIMARY KEY,
            time TEXT NOT NULL,
            repeat BOOLEAN DEFAULT 0,
            label TEXT,
            status TEXT DEFAULT 'active',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    # 5. NẠP DỮ LIỆU PHÒNG (Gắn ID cứng để dễ map với thiết bị)
    cursor.execute("SELECT COUNT(*) FROM rooms")
    if cursor.fetchone()[0] == 0:
        rooms_data = [
            (1, "Phòng Khách", "living_room"),
            (2, "Phòng Ngủ", "bedroom"),
            (3, "Nhà Bếp", "kitchen"),
            (4, "Sân vườn", "yard")
        ]
        cursor.executemany("INSERT OR IGNORE INTO rooms (id, name, slug) VALUES (?,?,?)", rooms_data)

    # 6. NẠP DỮ LIỆU THIẾT BỊ
    cursor.execute("SELECT COUNT(*) FROM devices")
    if cursor.fetchone()[0] == 0:
        print("Đang nạp dữ liệu thiết bị tĩnh...")
        
        # Cấu trúc: (id, room_id, name, type, pin, status)
        devices_data = [
            # --- 4 ĐÈN --- 
            (1, 1, 'Đèn Phòng Khách', 'light', 18, 'off'), 
            (2, 2, 'Đèn Phòng Ngủ', 'light', 19, 'off'),
            (3, 3, 'Đèn Bếp', 'light', 21, 'off'),
            (4, 4, 'Đèn Sân Vườn', 'light', 22, 'off'), # Đổi Hành Lang -> Sân Vườn (yard)
            
            # --- 4 QUẠT ---
            (5, 1, 'Quạt Phòng Khách', 'fan', 26, '0'),
            (6, 2, 'Quạt Phòng Ngủ', 'fan', 25, '0'),
            (7, 3, 'Quạt Bếp', 'fan', 33, '0'),
            (8, 3, 'Quạt Thông Gió', 'fan', 32, '0'), 
            
            # --- CẢM BIẾN, CỬA, LOA (Gán tạm vào Phòng Khách: room_id = 1) ---
            (9, 1, 'Cảm biến Nhiệt ẩm', 'sensor', 4, '0'),
            (10, 4, 'Cảm biến Ánh sáng', 'sensor', 35, '0'),
            (11, 1, 'Cửa Chính', 'door_lock', 13, 'locked'), # Chữ thường theo chuẩn API mới
            (12, 2, 'Loa', 'buzzer', 16, 'off')
        ]
        # Đã sửa câu lệnh INSERT khớp với 6 cột
        cursor.executemany("INSERT OR IGNORE INTO devices (id, room_id, name, type, pin, status) VALUES (?,?,?,?,?,?)", devices_data)
    
    conn.commit()
    conn.close()
    print("✅ Database đã sẵn sàng!")

def insert_sensor_data(device_id: int, value1: float, value2: float):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        if value2 == 0:
            status_text = f"{value1}" 
        else:
            status_text = f"{value1}°C - {value2}%" 
            
        cursor.execute("UPDATE devices SET status = ? WHERE id = ?", (status_text, device_id))
        
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("INSERT INTO device_history (device_id, status, timestamp) VALUES (?, ?, ?)", 
                       (device_id, status_text, current_time))
        
        conn.commit()
    except Exception as e:
        print(f"❌ Lỗi khi lưu Database: {e}")
    finally:
        conn.close()

def get_latest_sensor_data(device_id: int):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()

        query = """
            SELECT device_id, status, timestamp 
            FROM device_history 
            WHERE device_id = ? 
            ORDER BY timestamp DESC 
            LIMIT 1
        """ 
        cursor.execute(query, (device_id,))
        row = cursor.fetchone()
        
        if row:
            res = dict(row)
            status_str = res["status"]
            val1, val2 = 0.0, 0.0
            
            if "°C" in status_str:
                try:
                    parts = status_str.split(" - ")
                    val1 = float(parts[0].replace("°C", ""))
                    val2 = float(parts[1].replace("%", ""))
                except: pass
            else:
                try:
                    val1 = float(status_str)
                except: pass

            return {
                "device_id": res["device_id"],
                "value1": val1,
                "value2": val2,
                "timestamp": res["timestamp"],
                "raw_status": status_str 
            }
        return None
    except Exception as e:
        print(f"❌ Lỗi truy vấn Database: {e}")
        return None
    finally:
        conn.close()

def get_id_by_name(name: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM devices WHERE name = ?", (name,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return row["id"]
    return None

def parse_fan_status(status_str: str):
    try:      
        speed_val = int(status_str) 
        return {"speed": speed_val}
    except Exception as e:
        return {"speed": 0}

def delete_old_history():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        query = "DELETE FROM device_history WHERE timestamp < datetime('now', '-7 days')"
        cursor.execute(query)
        deleted_count = cursor.rowcount
        conn.commit()
        if deleted_count > 0:
            print(f"🧹 [Hệ thống] Đã dọn dẹp {deleted_count} bản ghi lịch sử cũ (trên 7 ngày).")
    except Exception as e:
        print(f"❌ Lỗi khi dọn dẹp Database: {e}")
    finally:
        conn.close()

def get_device_by_id(device_id : int) -> dict | None:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM devices WHERE id = ?", (device_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None

def get_devices_by_type(device_type : str) -> list[dict]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM devices WHERE type = ?", (device_type,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_devices_by_room(room_id : int) -> list[dict]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM devices WHERE room_id = ?", (room_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_room_by_slug(slug : str) -> dict | None:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM rooms WHERE slug = ?", (slug,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None

def update_device_status(device_id : int, status : str) -> bool:
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE devices SET status = ? WHERE id = ?", (status, device_id))
        conn.commit()
        return True
    except Exception as e:
        print(f"❌ Lỗi khi cập nhật trạng thái thiết bị: {e}")
        return False
    finally:
        conn.close()

def get_sensor_history(device_id: int, limit: int = 50, from_time: str = None, to_time: str = None) -> list[dict]:
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # Xây query linh hoạt: from_time và to_time là optional
        query = "SELECT device_id, status, timestamp FROM device_history WHERE device_id = ?"
        params = [device_id]
        
        if from_time:
            query += " AND timestamp >= ?"
            params.append(from_time)
        if to_time:
            query += " AND timestamp <= ?"
            params.append(to_time)
        
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except Exception as e:
        print(f"❌ Lỗi khi truy vấn lịch sử cảm biến: {e}")
        return []
    finally:
        conn.close()