import sqlite3
import os
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_NAME = os.path.join(BASE_DIR, "smarthome2.db")

def get_db_connection():
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    conn.row_factory = sqlite3.Row 
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. BẢNG THIẾT BỊ (Lưu trạng thái mới nhất - Giữ nguyên của em)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS devices (
            id INTEGER PRIMARY KEY,
            name TEXT,
            type TEXT, 
            pin INTEGER,
            status TEXT
        )
    ''')

    # 2. BẢNG LỊCH SỬ (THÊM MỚI)
    # Bảng này sẽ phình to theo thời gian, lưu lại mọi thay đổi
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS device_history (
            log_id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id INTEGER,
            status TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 3. Nạp dữ liệu tĩnh ban đầu
    cursor.execute("SELECT COUNT(*) FROM devices")
    if cursor.fetchone()[0] == 0:
        print("Đang nạp dữ liệu thiết bị tĩnh...")
      # Dữ liệu tĩnh ban đầu: 4 Đèn, 4 Quạt, 2 Cảm biến
    devices_data = [
            # --- 4 ĐÈN ---
            (1, 'Đèn Phòng Khách', 'light', 5, 'OFF'),
            (2, 'Đèn Phòng Ngủ', 'light', 19, 'OFF'),
            (3, 'Đèn Bếp', 'light', 21, 'OFF'),
            (4, 'Đèn Hành Lang', 'light', 22, 'OFF'),
            
            # --- 4 QUẠT (Chỉ còn pin tốc độ, status mặc định là '0') ---
            (5, 'Quạt Phòng Khách', 'fan', 18, '0'),
            (6, 'Quạt Phòng Ngủ', 'fan', 25, '0'),
            (7, 'Quạt Bếp', 'fan', 27, '0'),
            (8, 'Quạt Hành Lang', 'fan', 33, '0'), 
            
            # --- CẢM BIẾN, CỬA, LOA ---
            (9, 'Cảm biến Nhiệt ẩm', 'sensor', 4, '0'),
            (10, 'Cảm biến Ánh sáng', 'sensor', 32, '0'),
            (11, 'Cửa Chính', 'door', 15, 'CLOSED'),
            (12, 'Loa', 'buzzer', 16, 'OFF') # Hôm trước ta đã đổi loa sang chân 16
        ]
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS schedules (
            schedule_id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id INTEGER,
            command TEXT,           -- Lệnh sẽ gửi (VD: "ON", "OFF", hoặc chuỗi JSON cho quạt)
            trigger_time DATETIME,  -- Thời gian chính xác sẽ kích hoạt (VD: 2024-05-20 06:30:00)
            status TEXT DEFAULT 'PENDING', -- PENDING (Đang chờ), DONE (Đã xong), CANCELLED (Đã hủy)
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
   
    # Câu lệnh nạp vào DB (Bỏ qua nếu ID đã tồn tại để tránh lỗi)
    cursor.executemany("INSERT OR IGNORE INTO devices (id, name, type, pin, status) VALUES (?,?,?,?,?)", devices_data)
    
    conn.commit()
    conn.close()
    print("✅ Database đã sẵn sàng!")

def insert_sensor_data(device_id: int, value1: float, value2: float):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 1. Tạo chuỗi format
        if value2 == 0:
            status_text = f"{value1}" 
        else:
            status_text = f"{value1}°C - {value2}%" 
            
        # 2. Cập nhật bảng 'devices' (Để App luôn thấy số mới nhất)
        cursor.execute("UPDATE devices SET status = ? WHERE id = ?", (status_text, device_id))
        
        # 3. GHI VÀO BẢNG 'device_history' (THÊM MỚI)
        # Lấy giờ hệ thống hiện tại định dạng Năm-Tháng-Ngày Giờ:Phút:Giây
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("INSERT INTO device_history (device_id, status, timestamp) VALUES (?, ?, ?)", 
                       (device_id, status_text, current_time))
        
        conn.commit()
    except Exception as e:
        print(f"❌ Lỗi khi lưu Database: {e}")
    finally:
        conn.close()
def get_latest_sensor_data(device_id: int):
    try:
        conn = get_db_connection() 
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
        conn.close()
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
                # Trường hợp Cảm biến ánh sáng: "550"
                try:
                    val1 = float(status_str)
                except: pass

            # Trả về dictionary có các key mà API đang mong đợi (value1, value2)
            return {
                "device_id": res["device_id"],
                "value1": val1,
                "value2": val2,
                "timestamp": res["timestamp"],
                "raw_status": status_str # Giữ lại chuỗi gốc nếu cần
            }
        return None
    except Exception as e:
        print(f"❌ Lỗi truy vấn Database: {e}")
        return None


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
    """
    Hàm phân tích chuỗi status của quạt (VD: "2 - ON")
    Trả về Dictionary để trả cho App/Web hiển thị.
    """
    try:      
        speed_val = int(status_str) 
        return {
            "speed": speed_val
        }
    except Exception as e:
        # Nếu chuỗi bị lỗi hoặc quạt đang tắt, trả về mặc định
        return {"speed": 0}

def delete_old_history():
    """Xóa tất cả bản ghi trong device_history cũ hơn 7 ngày"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Sử dụng hàm datetime('now', '-7 days') của SQLite
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