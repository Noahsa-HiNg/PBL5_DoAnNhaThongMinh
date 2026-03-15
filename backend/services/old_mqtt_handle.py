import paho.mqtt.client as mqtt
import json
import threading
import database
# --- CẤU HÌNH BƯU ĐIỆN ---
MQTT_BROKER = "192.168.123.25"  # IP của Raspberry Pi (Khớp với ESP32)
MQTT_PORT = 1883
MQTT_TOPIC = "pbl5/sensor"

# Tạo một biến toàn cục để lưu tạm dữ liệu mới nhất (sau này sẽ thay bằng Database)
latest_data_light = {"light": 0, "state": "Chưa có dữ liệu"}
latest_data_temperature = {"temperature": 0}
latest_data_humidity = {"humidity": 0}

def on_connect(client, userdata, flags, rc):
    print(f"✅ [MQTT] Đã kết nối Bưu điện {MQTT_BROKER} thành công!")
    client.subscribe(MQTT_TOPIC + "/light")
    client.subscribe(MQTT_TOPIC + "/temperature")
    client.subscribe(MQTT_TOPIC + "/humidity")
    
    print(f"🎧 [MQTT] Đang lắng nghe tại topic: {MQTT_TOPIC} ...\n")

def on_message(client, userdata, msg):
    global latest_data_light, latest_data_temperature, latest_data_humidity
    chu_de_nhan_duoc = msg.topic
    if (chu_de_nhan_duoc == MQTT_TOPIC + "/light"):
        try:
            raw_data = msg.payload.decode('utf-8')
            data_dict = json.loads(raw_data)
            light = data_dict.get("light", 0)
            print(f"📥 [DATA MỚI] Nhận được độ sáng: {light}")
            latest_data_light["light"] = light
            latest_data_light["state"] = "Sáng chói" if light < 1000 else "Tối thui"
            database.save_sensor_data(1, light)
        except Exception as e:
            print(f"❌ [LỖI MQTT] Lỗi bóc tách dữ liệu: {e}")
    elif (chu_de_nhan_duoc == MQTT_TOPIC + "/temperature"):
        try:
            raw_data = msg.payload.decode('utf-8')
            data_dict = json.loads(raw_data)
            temperature = data_dict.get("temperature", 0)
            print(f"📥 [DATA MỚI] Nhận được nhiệt độ: {temperature}")
            latest_data_temperature["temperature"] = temperature
            database.save_sensor_data(2, temperature)
        except Exception as e:
            print(f"❌ [LỖI MQTT] Lỗi bóc tách dữ liệu: {e}")
    elif (chu_de_nhan_duoc == MQTT_TOPIC + "/humidity"):
        try:
            raw_data = msg.payload.decode('utf-8')
            data_dict = json.loads(raw_data)
            humidity = data_dict.get("humidity", 0)
            print(f"📥 [DATA MỚI] Nhận được độ ẩm: {humidity}")
            latest_data_humidity["humidity"] = humidity
            database.save_sensor_data(3, humidity)
        except Exception as e:
            print(f"❌ [LỖI MQTT] Lỗi bóc tách dữ liệu: {e}")

# Hàm này dùng để chạy MQTT chạy ngầm (Background Thread)
def start_mqtt():
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.loop_forever() # Vòng lặp vĩnh cửu nghe ngóng
    except Exception as e:
        print(f"❌ [LỖI MQTT] Không thể kết nối tới Broker: {e}")

# Khởi động MQTT trên một luồng riêng để không làm kẹt Web Server
def run_mqtt_thread():
    thread = threading.Thread(target=start_mqtt)
    thread.daemon = True
    thread.start()