from fastapi import FastAPI
from mqtt_handler import run_mqtt_thread
import mqtt_handler  
import database
# Khởi tạo Web Server siêu tốc
app = FastAPI(title="PBL5 Smart Home Backend")

# Khi Server vừa bật lên, lập tức đánh thức ông Thủ kho MQTT đi làm
@app.on_event("startup")
def startup_event():
    print("🚀 Đang khởi động hệ thống...")
    database.init_db()
    run_mqtt_thread()

@app.get("/api/sensor/latest")
def get_all_latest():
    """Lấy tất cả dữ liệu mới nhất từ RAM để hiển thị nhanh"""
    return {
        "light": mqtt_handler.latest_data_light,
        "temperature": mqtt_handler.latest_data_temperature,
        "humidity": mqtt_handler.latest_data_humidity
    }
#data 

@app.get("/api/sensor/history/{device_id}")
def get_sensor_history(device_id: int, limit: int = 20):
    """Lấy lịch sử N bản ghi gần nhất của một cảm biến để vẽ biểu đồ"""
    data = database.get_sensor_history(device_id, limit)
    if not data:
        raise HTTPException(status_code=404, detail="Không tìm thấy dữ liệu cho ID này")
    return data

@app.get("/api/device/status/{device_id}")
def get_device_status(device_id: int):
    """Kiểm tra xem đèn/quạt hiện tại đang ON hay OFF trong DB"""
    status = database.get_latest_status(device_id)
    return {"device_id": device_id, "status": status}

@app.post("/api/control/device/{device_id}")
def control_device(device_id: int, command: str):
    command = command.upper()
    if command not in ["ON", "OFF"]:
        raise HTTPException(status_code=400, detail="Lệnh phải là ON hoặc OFF")

    # BƯỚC 1: Gửi lệnh qua MQTT xuống ESP32
    target_topic = f"pbl5/control/device/{device_id}"
    mqtt_handler.gui_len_mqtt(target_topic, command)

    # BƯỚC 2: Cập nhật trạng thái mới vào Database
    database.update_device_status(device_id, command)

    return {
        "status": "Success",
        "device_id": device_id,
        "command": command
    }
# API 1: Kiểm tra xem Server có sống không
@app.get("/")
def he_thong_status():
    return {"message": "Hệ thống AIoT PBL5 đang chạy mượt mà!"}

@app.get("/api/sensor/latest/light")
def get_latest_light_sensor_data():
    return mqtt_handler.latest_data_light

@app.get("/api/sensor/latest/temperature")
def get_latest_temperature_sensor_data():
    return mqtt_handler.latest_data_temperature

@app.get("/api/sensor/latest/humidity")
def get_latest_humidity_sensor_data():
    return mqtt_handler.latest_data_humidity

# (Sau này sẽ viết thêm API 3: /api/control để bật tắt đèn)
@app.post("/api/control/device/{device_id}")
def control_device(device_id: int, command: str):
    cmd = command.upper()
    if cmd not in ["ON", "OFF"]:
        return {"error": "Lệnh chỉ được là ON hoặc OFF"}
    # Tự động tạo Topic dựa trên ID người dùng gửi lên
    target_topic = f"pbl5/control/device/{device_id}"
    # 1. Gửi lệnh MQTT
    mqtt_handler.gui_len_mqtt(target_topic, cmd)
    # 2. Cập nhật trạng thái vào Database
    database.update_device_status(device_id, cmd)

    return {"status": "success", "device": device_id, "cmd": cmd}



@app.get("/api/esp32/config")
def get_config_for_esp32():
    """
    API phục vụ riêng cho ESP32 lấy cấu hình chân Pin và ID thiết bị.
    Dữ liệu lấy trực tiếp từ bảng 'devices' trong Database.
    """
    try:
        config_data = database.get_esp32_config()
        
        if not config_data:
            return [] # Trả về mảng rỗng nếu chưa có thiết bị nào
            
        print(f"📡 [API] Đã gửi cấu hình cho ESP32: {len(config_data)} thiết bị.")
        return config_data
        
    except Exception as e:
        print(f"❌ [API ERROR] Lỗi khi lấy cấu hình: {e}")
        return {"error": str(e)}

@app.get("/api/device/pin/{pin_number}")
def get_device_by_pin(pin_number: int):
    """
    API phục vụ riêng cho ESP32 kiểm tra xem chân Pin này có thiết bị nào không.
    """
    try:
        device = database.get_device_by_pin(pin_number)
        
        if not device:
            return {"error": "Không tìm thấy thiết bị tại chân này"}
            
        # Trả về thông tin cơ bản: ID, Type, Name
        return {
            "id": device["id"],
            "type": device["type"],
            "name": device["name"]
        }
        
    except Exception as e:
        print(f"❌ [API ERROR] Lỗi khi lấy thông tin thiết bị theo Pin: {e}")
        return {"error": str(e)}
        