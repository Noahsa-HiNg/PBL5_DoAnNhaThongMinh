import json

class IoTController:
    def __init__(self, repo, mqtt_service):
        self.repo = repo
        self.mqtt = mqtt_service
        # Đăng ký nhận tin nhắn từ MQTT Service
        self.mqtt.on_message_received = self.handle_sensor_data

    def handle_sensor_data(self, topic, payload):
        """Xử lý dữ liệu từ ESP32 gửi lên"""
        try:
            data = json.loads(payload)
            device_id = data.get("id")
            value = data.get("value")
            # Controller bảo Repo lưu vào DB
            self.repo.save_sensor_data(device_id, value)
            print(f"✅ Đã lưu dữ liệu ID {device_id}: {value}")
        except Exception as e:
            print(f"❌ Lỗi xử lý sensor: {e}")

    def control_device(self, device_id, command):
        topic = f"pbl5/control/device/{device_id}"
        self.mqtt.publish(topic, command.upper())
        self.repo.update_status(device_id, command)
        return {"status": "success", "device_id": device_id}
    
    def get_temperature_logic(self, device_id: int):
        raw_data = self.repo.get_latest_temperature(device_id)
        
        if not raw_data:
            return {"error": "Không tìm thấy dữ liệu cho thiết bị này"}

        return {
            "device_id": device_id,
            "device_name": raw_data["device_name"],
            "room_name": raw_data["room_name"],
            "value": round(raw_data["value"], 2),
            "unit": raw_data["unit"],
            "time": raw_data["timestamp"]
        }