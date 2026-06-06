import socketio

# Cấu hình Socket.IO Server — Engine.IO v3 (tương thích Client v2.x)
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

    async def broadcast_sensor_update(self, device_id: int, value1: float, value2: float | None, unit1: str, unit2: str | None):
        """
        Broadcast cập nhật cảm biến theo format yêu cầu của Android App.

        Payload:
            {"device_id": int, "type": "sensor", "data": {"value1": float, "value2": float/null, "unit1": str, "unit2": str/null}}
        """
        data = {
            "value1": value1,
            "value2": value2,
            "unit1": unit1,
            "unit2": unit2,
        }
        payload = {
            "device_id": device_id,
            "type": "sensor",
            "data": data
        }
        await sio.emit("sensor_update", payload)
        print(f"📤 Broadcast sensor_update: {payload}")

    async def broadcast_device_update(self, device_id: int, device_type: str, name: str, data: dict):
        """
        Broadcast cập nhật trạng thái thiết bị.

        Payload:
            {"device_id": int, "type": str, "name": str, "data": {"state": "on"/"off", ...}}
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

        Payload:
            {"label": str, "time": str}
        """
        payload = {
            "label": label,
            "time": time
        }
        await sio.emit("alarm_triggered", payload)
        print(f"📤 Broadcast alarm_triggered: {payload}")

# Singleton
socketio_manager = SocketIOManager()