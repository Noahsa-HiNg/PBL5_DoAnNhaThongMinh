import paho.mqtt.client as mqtt
import json
import asyncio
from core.config import MQTT_BROKER, MQTT_PORT
from core.database import insert_sensor_data
from core.ws_manager import socketio_manager

class MQTTManager:
    def __init__(self):
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
        self.broker = MQTT_BROKER
        self.port = MQTT_PORT
        # Lưu event loop của asyncio để broadcast từ thread MQTT
        self._loop: asyncio.AbstractEventLoop | None = None

    def set_loop(self, loop: asyncio.AbstractEventLoop):
        """Được gọi từ lifespan (asyncio context) để lưu đúng event loop."""
        self._loop = loop

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print("✅ Đã kết nối với MQTT Broker!")
            self.client.subscribe("home/sensors/#")
        else:
            print(f"❌ Lỗi kết nối MQTT, mã lỗi: {rc}")

    def on_message(self, client, userdata, msg):
        topic = msg.topic
        payload = msg.payload.decode()

        if topic.startswith("home/sensors/"):
            try:
                device_id = int(topic.split("/")[-1])
                data = json.loads(payload)

                if "temp" in data:
                    # ── DHT11: Nhiệt độ & Độ ẩm ──
                    insert_sensor_data(device_id, data["temp"], data.get("humi", 0))
                    print(f"📥 Cảm biến ID {device_id} (DHT11): {data['temp']}°C, {data['humi']}%")

                    # Push xuống mobile qua Socket.IO
                    self._broadcast_sensor_update(device_id, "temperature", {
                        "value": data["temp"],
                        "unit": "C"
                    })

                elif "light" in data:
                    # ── Cảm biến Ánh sáng ──
                    insert_sensor_data(device_id, data["light"], 0)
                    print(f"📥 Cảm biến ID {device_id} (Ánh sáng): {data['light']}")

                    # Push xuống mobile qua Socket.IO
                    self._broadcast_sensor_update(device_id, "light_sensor", {
                        "value": data["light"],
                        "unit": "lux"  # Giả sử đơn vị là lux
                    })

            except Exception as e:
                print(f"❌ Lỗi xử lý MQTT message: {e}")

    def _broadcast_sensor_update(self, device_id: int, sensor_type: str, data: dict):
        """
        Gửi cập nhật cảm biến qua Socket.IO.
        """
        if self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(
                socketio_manager.broadcast_sensor_update(device_id, sensor_type, data),
                self._loop
            )

    def start(self):
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        try:
            # Lấy running loop từ asyncio context (FastAPI lifespan)
            # An toàn hơn get_event_loop() trên Python 3.10+
            self._loop = asyncio.get_running_loop()
        except RuntimeError:
            self._loop = None
        try:
            self.client.connect(self.broker, self.port, 60)
            self.client.loop_start()
        except Exception as e:
            print(f"⚠️ Không tìm thấy MQTT Broker (Mosquitto) đang chạy. Lỗi: {e}")

    def publish_command(self, device_id: int, command: str):
        """Hàm dùng để ra lệnh Bật/Tắt gửi xuống ESP32"""
        topic = f"home/control/device/{device_id}"
        self.client.publish(topic, command)
        print(f"📤 Đã gửi lệnh [{command}] xuống topic [{topic}]")

# Singleton — dùng chung toàn dự án
mqtt_service = MQTTManager()