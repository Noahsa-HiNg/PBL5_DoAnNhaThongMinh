"""
socketio_server.py — Server mini chay Socket.IO + REST API
KHONG can: AI pipeline, MQTT Broker, phan cung Raspberry.

Van de: Khong duoc mount socketio.ASGIApp vao cung FastAPI app (gay recursion).
Giai phap: socketio.ASGIApp la app chinh, FastAPI la other_asgi_app.

Chay:  python -m uvicorn backend.socketio_server:asgi_app --host 0.0.0.0 --port 8000 --reload
"""

import os
import sys
from pathlib import Path

# Them thu muc backend vao sys.path de import duoc core.*
BACKEND_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BACKEND_DIR))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn
import asyncio
import random
import socketio
from datetime import datetime
from core.ws_manager import sio, socketio_manager
from core.database import init_db
from core.config import SERVER_PORT

# --- Mock data ---------------------------------------------------------
_sensor_mock = {
    9:  {"value1": 28.5, "value2": 65.0, "unit1": "C", "unit2": "%"},     # DHT11
    10: {"value1": 350.0, "value2": None, "unit1": "lux", "unit2": None},  # Light
}

_device_mock = {
    1:  {"type": "light", "name": "Den Phong Khach", "state": "off"},
    2:  {"type": "light", "name": "Den Phong Ngu", "state": "off"},
    3:  {"type": "light", "name": "Den Bep", "state": "off"},
    4:  {"type": "light", "name": "Den San Vuon", "state": "off"},
    5:  {"type": "fan", "name": "Quat Phong Khach", "state": "off", "speed": 0},
    6:  {"type": "fan", "name": "Quat Phong Ngu", "state": "off", "speed": 0},
    7:  {"type": "fan", "name": "Quat Bep", "state": "off", "speed": 0},
    8:  {"type": "fan", "name": "Quat Thong Gio", "state": "off", "speed": 0},
    9:  {"type": "sensor", "name": "Cam bien Nhiet am"},
    10: {"type": "sensor", "name": "Cam bien Anh sang"},
    11: {"type": "door_lock", "name": "Cua Chinh", "state": "locked"},
    12: {"type": "buzzer", "name": "Loa", "state": "off"},
}


async def mock_sensor_worker():
    """Gia lap cam bien: moi 10s random data + broadcast qua Socket.IO"""
    while True:
        try:
            temp = round(random.uniform(25.0, 35.0), 1)
            humi = round(random.uniform(50.0, 80.0), 1)
            lux = round(random.uniform(50.0, 800.0), 1)

            _sensor_mock[9]  = {"value1": temp, "value2": humi, "unit1": "C", "unit2": "%"}
            _sensor_mock[10] = {"value1": lux,  "value2": None, "unit1": "lux", "unit2": None}

            await socketio_manager.broadcast_sensor_update(9, temp, humi, "C", "%")
            await socketio_manager.broadcast_sensor_update(10, lux, None, "lux", None)

        except Exception as e:
            print(f"[Loi mock sensor worker] {e}")

        await asyncio.sleep(10)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Khoi dong server mini -- khong can MQTT, khong can AI"""
    print("[Socket.IO Mini Server] Dang khoi dong...")

    try:
        init_db()
        print("[DB] Database da san sang")
    except Exception as e:
        print(f"[DB] Khong kha dung: {e} (Socket.IO van chay)")

    asyncio.create_task(mock_sensor_worker())

    yield

    print("[Socket.IO Mini Server] Dang dung...")

# --- FastAPI app (chi chua REST APIs) -----------------------------------
fastapi_app = FastAPI(
    title="PBL5 Smart Home API -- Socket.IO Mini",
    description="Server mini chi chay Socket.IO + mock data",
    version="2.0.0-socketio",
    lifespan=lifespan
)

fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Socket.IO Events -------------------------------------------------
@sio.event
async def connect(sid, environ):
    print(f"[Socket.IO] Client {sid} connected")

@sio.event
async def disconnect(sid):
    print(f"[Socket.IO] Client {sid} disconnected")


# --- REST Endpoints (FastAPI) ------------------------------------------

@fastapi_app.get("/")
def root():
    return {"message": "PBL5 Smart Home Socket.IO Mini Server dang hoat dong!"}

@fastapi_app.get("/api/health")
def health_check():
    return {
        "status": "success",
        "message": "Socket.IO Mini Server OK",
        "data": {
            "version": "2.0.0-socketio",
            "mqtt_connected": False,
        }
    }

@fastapi_app.get("/api/mock/sensors")
def get_mock_sensors():
    return {
        "status": "success",
        "data": {
            "dht11": _sensor_mock[9],
            "light": _sensor_mock[10],
            "timestamp": datetime.now().isoformat()
        }
    }

@fastapi_app.get("/api/mock/devices")
def get_mock_devices():
    return {
        "status": "success",
        "data": {
            "devices": [
                {"device_id": did, **info}
                for did, info in _device_mock.items()
            ]
        }
    }

@fastapi_app.post("/api/mock/device/{device_id}/{action}")
async def control_mock_device(device_id: int, action: str):
    if device_id not in _device_mock:
        return {"status": "error", "message": "Thiet bi khong ton tai"}

    device = _device_mock[device_id]
    dtype = device["type"]

    if dtype == "light" or dtype == "buzzer":
        if action not in ("on", "off"):
            return {"status": "error", "message": "Chi on/off"}
        device["state"] = action
        await socketio_manager.broadcast_device_update(device_id, dtype, device["name"], {"state": action})

    elif dtype == "fan":
        if action == "on":
            device["state"] = "on"
            device["speed"] = 2
            await socketio_manager.broadcast_device_update(device_id, dtype, device["name"], {"state": "on", "speed": 2})
        elif action == "off":
            device["state"] = "off"
            device["speed"] = 0
            await socketio_manager.broadcast_device_update(device_id, dtype, device["name"], {"state": "off", "speed": 0})
        else:
            return {"status": "error", "message": "Chi on/off"}

    elif dtype == "door_lock":
        if action not in ("lock", "unlock"):
            return {"status": "error", "message": "Chi lock/unlock"}
        device["state"] = action
        await socketio_manager.broadcast_device_update(device_id, dtype, device["name"], {"state": action})

    else:
        return {"status": "error", "message": "Loai thiet bi khong ho tro"}

    return {
        "status": "success",
        "message": f"Da {action} {device['name']}",
        "data": {"device_id": device_id, "device": device}
    }

@fastapi_app.post("/api/mock/alarm")
async def trigger_mock_alarm():
    now = datetime.now()
    label = "Bao thuc test"
    time_str = now.strftime("%H:%M")
    await socketio_manager.broadcast_alarm_triggered(label, time_str)
    return {
        "status": "success",
        "message": f"Da broadcast alarm_triggered: {label} luc {time_str}"
    }

@fastapi_app.post("/api/mock/sensor-update/{device_id}")
async def trigger_mock_sensor_update(device_id: int):
    if device_id == 9:
        val1 = round(random.uniform(25.0, 35.0), 1)
        val2 = round(random.uniform(50.0, 80.0), 1)
        await socketio_manager.broadcast_sensor_update(9, val1, val2, "C", "%")
        return {"status": "success", "message": f"Da broadcast DHT11: {val1}C, {val2}%"}
    elif device_id == 10:
        val1 = round(random.uniform(50.0, 800.0), 1)
        await socketio_manager.broadcast_sensor_update(10, val1, None, "lux", None)
        return {"status": "success", "message": f"Da broadcast Light: {val1} lux"}
    else:
        return {"status": "error", "message": "Chi ho tro device_id 9 (DHT11) hoac 10 (Anh sang)"}


# --- ASGI app chinh: Socket.IO se handle /socket.io/, FastAPI handle phan con lai ---
asgi_app = socketio.ASGIApp(sio, other_asgi_app=fastapi_app)


if __name__ == "__main__":
    uvicorn.run("socketio_server:asgi_app", host="0.0.0.0", port=SERVER_PORT, reload=True)