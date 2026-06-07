import socketio

# Cau hinh Socket.IO Server -- Engine.IO v3 (tuong thich Client v2.x)
sio = socketio.AsyncServer(
    async_mode='asgi',
    cors_allowed_origins='*',  # Cho phep tat ca origins cho dev
    logger=True,
    engineio_logger=True
)

class SocketIOManager:
    """
    Quan ly Socket.IO connections va broadcast.
    Dung chung toan du an -- import sio tu file nay.
    """

    async def broadcast_sensor_update(self, device_id: int, value1: float, value2: float | None, unit1: str, unit2: str | None):
        """
        Broadcast cap nhat cam bien theo format yeu cau cua Android App.

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
        print(f"[SIO] Broadcast sensor_update: {payload}")

    async def broadcast_device_update(self, device_id: int, device_type: str, name: str, data: dict):
        """
        Broadcast cap nhat trang thai thiet bi.

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
        print(f"[SIO] Broadcast device_update: {payload}")

    async def broadcast_schedule_updated(self, action: str, schedule_id: int, device_name: str, command: str, execute_at: str):
        """
        Broadcast khi co thay doi lich hen gio (tao/huy).

        Payload:
            {"action": "create"/"cancel", "schedule_id": int, "device_name": str, "command": str, "execute_at": str}
        """
        payload = {
            "action": action,
            "schedule_id": schedule_id,
            "device_name": device_name,
            "command": command,
            "execute_at": execute_at
        }
        await sio.emit("schedule_updated", payload)
        print(f"[SIO] Broadcast schedule_updated: {payload}")

    async def broadcast_alarm_triggered(self, label: str, time: str):
        """
        Broadcast kich hoat bao thuc.

        Payload:
            {"label": str, "time": str}
        """
        payload = {
            "label": label,
            "time": time
        }
        await sio.emit("alarm_triggered", payload)
        print(f"[SIO] Broadcast alarm_triggered: {payload}")

# Singleton
socketio_manager = SocketIOManager()