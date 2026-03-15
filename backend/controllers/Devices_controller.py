from models.schemas import DeviceCreate,DeviceResponse,DeviceDetailResponse,DeviceUpdate,DeviceStatusResponse
from repositories.Devices_repo import DeviceRepo

class DeviceController:
    def __init__(self):
        self.repo = DeviceRepo()
    def add_new_device(self, device_data: DeviceCreate):
        result = self.repo.create_device(device_data)
        if result.get("error"):
            return {"error": "Thiết bị này đã tồn tại!"}
        return result
    def get_all_devices(self):
        return self.repo.get_all_devices()
    def get_device_by_id(self, device_id: int):
        return self.repo.get_device_by_id(device_id)
    def delete_device(self, device_id: int):
        return self.repo.delete_device(device_id)
    def update_device(self, device_id: int, device: DeviceUpdate):
        return self.repo.update_device(device_id, device)
    def get_device_status(self, device_id: int):
        return self.repo.get_device_status(device_id)
    def control_device(self, device_id: int, status: str):
        if status not in ["ON", "OFF"]:
            return {"error": "Trạng thái chỉ được là 'ON' hoặc 'OFF'"}
        
        # 1. Cập nhật DB
        db_result = self.repo.update_device_status(device_id, status)
        if db_result.get("error"):
            return db_result

        # 2. Ở NÂNG CAO: Chỗ này sau sẽ gọi MQTT để publish lệnh xuống ESP32
        # mqtt_svc.publish(f"smarthome/control/{mac_address}", {"pin": pin, "state": status})
        
        return {"message": f"Đã gửi lệnh {status} tới thiết bị {device_id}"}