import sqlite3
from datetime import datetime, timedelta

DB_NAME = "smarthome.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Bật kiểm tra Khóa ngoại (Bắt buộc để ERD hoạt động đúng)
    cursor.execute("PRAGMA foreign_keys = ON")

    # ==========================================
    # 1. CÁC BẢNG DANH MỤC (MASTER DATA)
    # ==========================================
    
    # 1.1. Bảng Phòng
    cursor.execute('''CREATE TABLE IF NOT EXISTS rooms (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE
    )''')

    # 1.2. Bảng Loại thiết bị
    cursor.execute('''CREATE TABLE IF NOT EXISTS device_types (
        id INTEGER PRIMARY KEY,
        type_name TEXT NOT NULL UNIQUE,  -- Vd: SENSOR_TEMP, RELAY_LIGHT, RELAY_FAN
        unit TEXT,                       -- Vd: °C, %, None
        category TEXT NOT NULL           -- 'sensor' hoặc 'actuator' (Để phân biệt logic)
    )''')

    # 1.3. Bảng Các Board ESP32 (Node)
    cursor.execute('''CREATE TABLE IF NOT EXISTS esp_nodes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        mac_address TEXT UNIQUE,         -- Địa chỉ MAC để nhận diện chính xác phần cứng
        location_desc TEXT               -- Vd: "Tủ điện phòng khách", "Trần thạch cao"
    )''')

    # ==========================================
    # 2. BẢNG TRUNG TÂM (TRANSACTION DATA)
    # ==========================================

    # 2.1. Bảng Thiết bị
    cursor.execute('''CREATE TABLE IF NOT EXISTS devices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        room_id INTEGER NOT NULL,
        type_id INTEGER NOT NULL,
        esp_id INTEGER NOT NULL,
        pin INTEGER NOT NULL,
        
        -- Ràng buộc Khóa ngoại
        FOREIGN KEY (room_id) REFERENCES rooms (id) ON DELETE CASCADE,
        FOREIGN KEY (type_id) REFERENCES device_types (id),
        FOREIGN KEY (esp_id) REFERENCES esp_nodes (id) ON DELETE CASCADE,
        
        -- Ràng buộc logic: Một board ESP32 không thể có 2 thiết bị cắm chung 1 chân Pin
        UNIQUE(esp_id, pin) 
    )''')

    # ==========================================
    # 3. CÁC BẢNG LƯU TRỮ TRẠNG THÁI & LỊCH SỬ
    # ==========================================

    # 3.1. Trạng thái thiết bị điều khiển (Chỉ lưu dòng mới nhất)
    cursor.execute('''CREATE TABLE IF NOT EXISTS device_status (
        device_id INTEGER PRIMARY KEY,
        status TEXT NOT NULL,
        last_changed DATETIME NOT NULL,
        FOREIGN KEY (device_id) REFERENCES devices (id) ON DELETE CASCADE
    )''')

    # 3.2. Lịch sử cảm biến (Lưu vô hạn, có cơ chế tự xóa)
    cursor.execute('''CREATE TABLE IF NOT EXISTS sensor_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        device_id INTEGER NOT NULL,
        value FLOAT NOT NULL,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (device_id) REFERENCES devices (id) ON DELETE CASCADE
    )''')

    # ==========================================
    # 4. NÊM DỮ LIỆU MẪU (SEED DATA)
    # ==========================================
    cursor.execute("SELECT COUNT(*) FROM rooms")
    if cursor.fetchone()[0] == 0:
        # Thêm Phòng
        cursor.executemany("INSERT INTO rooms (id, name) VALUES (?,?)", 
                           [(1, 'Phòng Khách'), (2, 'Phòng Ngủ 1')])
        
        # Thêm Loại thiết bị (Phân loại rõ Sensor và Actuator)
        cursor.executemany("INSERT INTO device_types (id, type_name, unit, category) VALUES (?,?,?,?)", [
            (1, 'SENSOR_TEMP', '°C', 'sensor'),
            (2, 'SENSOR_HUMI', '%', 'sensor'),
            (3, 'RELAY_LIGHT', None, 'actuator'),
            (4, 'RELAY_FAN', None, 'actuator')
        ])

        # Thêm 2 con ESP32 vào hệ thống
        cursor.executemany("INSERT INTO esp_nodes (id, mac_address, location_desc) VALUES (?,?,?)", [
            (1, 'A1:B2:C3:D4:E5:F6', 'Tủ điện Tầng 1'),
            (2, '11:22:33:44:55:66', 'Trần Phòng Ngủ')
        ])

        # Thêm Thiết bị (Gắn vào đúng Phòng, đúng Loại, đúng ESP, đúng Pin)
        cursor.executemany("INSERT INTO devices (id, name, room_id, type_id, esp_id, pin) VALUES (?,?,?,?,?,?)", [
            (10, 'Cảm biến nhiệt PK', 1, 1, 1, 4),  # ESP1, Pin 4
            (11, 'Đèn chính PK',      1, 3, 1, 5),  # ESP1, Pin 5
            (12, 'Đèn ngủ PN1',       2, 3, 2, 5),  # ESP2, Pin 5 (Trùng pin với đèn trên không sao vì khác ESP)
            (13, 'Quạt trần PN1',     2, 4, 2, 18)  # ESP2, Pin 18
        ])

        # Khởi tạo trạng thái OFF cho các thiết bị Actuator (Đèn, Quạt)
        cursor.executemany("INSERT INTO device_status (device_id, status, last_changed) VALUES (?,?,?)", [
            (11, 'OFF', datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
            (12, 'OFF', datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
            (13, 'OFF', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        ])

    conn.commit()
    conn.close()
    print("✅ [DATABASE] Đã khởi tạo Sơ đồ ERD chuẩn mực thành công!")
if __name__ == "__main__":
    init_db()