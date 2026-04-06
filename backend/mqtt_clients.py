import paho.mqtt.client as mqtt
import json

# Import hàm lưu Database mà em đã viết ở file database.py
from database import insert_sensor_data 

class MQTTManager:
    def __init__(self):
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
        self.broker = "172.20.10.2" # IP của em rất chuẩn
        self.port = 1883

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print("✅ Đã kết nối với MQTT Broker!")
            
            # SỬA LỖI 1: Đăng ký nghe TẤT CẢ các ID cảm biến bằng dấu '#'
            # (Thay vì "home/esp32/sensors" như cũ)
            self.client.subscribe("home/sensors/#")
        else:
            print(f"❌ Lỗi kết nối MQTT, mã lỗi: {rc}")

    def on_message(self, client, userdata, msg):
        topic = msg.topic
        payload = msg.payload.decode()
        
        # SỬA LỖI 2: Code logic bóc tách JSON và lưu thẳng vào SQLite
        if topic.startswith("home/sensors/"):
            try:
                # Cắt chuỗi lấy ID ở cuối (VD: "home/sensors/3" -> Lấy số 3)
                device_id = int(topic.split("/")[-1])
                data = json.loads(payload)
                
                # Phân loại Cảm biến để lưu Database
                if "temp" in data:
                    # Nếu là DHT11
                    insert_sensor_data(device_id, data["temp"], data.get("humi", 0))
                    print(f"📥 Cảm biến ID {device_id} (DHT11): {data['temp']}°C, {data['humi']}%")
                    
                elif "light" in data:
                    # Nếu là Cảm biến ánh sáng
                    insert_sensor_data(device_id, data["light"], 0)
                    print(f"📥 Cảm biến ID {device_id} (Ánh sáng): {data['light']}")
                    
            except Exception as e:
                print(f"❌ Lỗi xử lý MQTT message: {e}")

    def start(self):
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        try:
            self.client.connect(self.broker, self.port, 60)
            self.client.loop_start() 
        except Exception as e:
            print(f"⚠️ Không tìm thấy MQTT Broker (Mosquitto) đang chạy. Lỗi: {e}")

    def publish_command(self, device_id: int, command: str):
        """Hàm dùng để ra lệnh Bật/Tắt gửi xuống ESP32"""

        # ESP32 đang lắng nghe "home/control/device/#"
        topic = f"home/control/device/{device_id}"
        
        self.client.publish(topic, command)
        print(f"📤 Đã gửi lệnh [{command}] xuống topic [{topic}]")

# Tạo 1 biến dùng chung cho toàn dự án
mqtt_service = MQTTManager()