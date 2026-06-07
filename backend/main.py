"""
main.py — Smart Home Backend Server (FastAPI + Socket.IO)
Fix: Sua loi recursion khi mount socketio.ASGIApp.

Chay:  python -m uvicorn backend.main:asgi_app --host 0.0.0.0 --port 8000 --reload
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn
import asyncio
import socketio
from core.ws_manager import sio
from core.database import init_db
from core.config import SERVER_PORT
from services.mqtt_service import mqtt_service
from workers.worker import cleanup_worker
from routers import (
    system_routers,
    status_routers,
    sensor_routers,
    control_routers,
    schedule_routers,
    bulk_routers,
    weather_routers,
    context_routers,
    voice_routers,
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Khoi dong va don dep tai nguyen khi server bat/tat"""
    print("[Server] Dang khoi dong Smart Home Server...")

    # Khoi tao Database
    init_db()

    # Ket noi MQTT Broker
    mqtt_service.start()

    # Chay Background Workers
    asyncio.create_task(cleanup_worker())

    yield  # Server dang chay

    # Tat server
    print("[Server] Dang tat Server...")
    mqtt_service.client.loop_stop()
    mqtt_service.client.disconnect()

# --- FastAPI app (chi chua REST APIs) -------------------------------
fastapi_app = FastAPI(
    title="PBL5 Smart Home API",
    description="REST API cho he thong nha thong minh -- PBL5 DHBK Da Nang",
    version="2.0.0",
    lifespan=lifespan
)

fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Dang ky tat ca Routers ---
fastapi_app.include_router(system_routers.router)      # /api/health, /api/time
fastapi_app.include_router(status_routers.router)       # /api/status/...
fastapi_app.include_router(sensor_routers.router)       # /api/sensors/...
fastapi_app.include_router(control_routers.router)      # /api/control/...
fastapi_app.include_router(schedule_routers.router)     # /api/schedules/...
fastapi_app.include_router(bulk_routers.router)         # /api/bulk/...
fastapi_app.include_router(weather_routers.router)      # /api/weather/...
fastapi_app.include_router(context_routers.router)      # /api/context/...
fastapi_app.include_router(voice_routers.router)        # /api/voice/...

@fastapi_app.get("/", tags=["He thong"])
def root():
    return {"message": "PBL5 Smart Home Server v2.0 dang hoat dong!"}

# --- Socket.IO Events ---
@sio.event
async def connect(sid, environ):
    print(f"[Socket.IO] Client {sid} connected")

@sio.event
async def disconnect(sid):
    print(f"[Socket.IO] Client {sid} disconnected")

# --- ASGI app chinh: Socket.IO se handle /socket.io/, FastAPI handle phan con lai ---
asgi_app = socketio.ASGIApp(sio, other_asgi_app=fastapi_app)

if __name__ == "__main__":
    uvicorn.run("main:asgi_app", host="0.0.0.0", port=SERVER_PORT, reload=True)