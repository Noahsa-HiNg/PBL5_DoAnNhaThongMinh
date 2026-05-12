import socketio

# Cấu hình Socket.IO Server
sio = socketio.AsyncServer(
    async_mode='asgi',
    cors_allowed_origins='*',  # Cho phép tất cả origins cho dev
    logger=True,
    engineio_logger=True
)

class SocketIOManager:
    """
    Quản lý Socket.IO connections và broadcast.
    Dùng chung toàn dự án — import sio từ file này.
    """

    async def broadcast_sensor_update(self, device_id: int, sensor_type: str, data: dict):
        """
        Broadcast cập nhật cảm biến theo format yêu cầu.
        """
        payload = {
            "device_id": device_id,
            "type": sensor_type,
            "data": data
        }
        await sio.emit("sensor_update", payload)
        print(f"📤 Broadcast sensor_update: {payload}")

    async def broadcast_device_update(self, device_id: int, device_type: str, name: str, data: dict):
        """
        Broadcast cập nhật trạng thái thiết bị.
        """
        payload = {
            "device_id": device_id,
            "type": device_type,
            "name": name,
            "data": data
        }
        await sio.emit("device_update", payload)
        print(f"📤 Broadcast device_update: {payload}")

    async def broadcast_alarm_triggered(self, label: str, time: str):
        """
        Broadcast kích hoạt báo thức.
        """
        payload = {
            "data": {
                "label": label,
                "time": time
            }
        }
        await sio.emit("alarm_triggered", payload)
        print(f"📤 Broadcast alarm_triggered: {payload}")

# Singleton
socketio_manager = SocketIOManager()