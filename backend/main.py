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
from workers.worker import alarm_worker, buzzer_alarm_worker, cleanup_worker
from routers import (
    system_routers,
    status_routers,
    sensor_routers,
    control_routers,
    schedule_routers,
    alarm_routers,
    bulk_routers,
    weather_routers,
    context_routers,
    voice_routers,
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Khởi động và dọn dẹp tài nguyên khi server bật/tắt"""
    print("🚀 Đang khởi động Smart Home Server...")

    # Khởi tạo Database
    init_db()

    # Kết nối MQTT Broker
    mqtt_service.start()

    # Khởi động AI Pipeline (STT + NLU + DM + NLG + TTS) — load 1 lần duy nhất
    voice_routers.init_pipeline()

    # Chạy Background Workers
    asyncio.create_task(alarm_worker())
    asyncio.create_task(buzzer_alarm_worker())
    asyncio.create_task(cleanup_worker())

    yield  # Server đang chạy

    # Tắt server
    print("🛑 Đang tắt Server...")
    mqtt_service.client.loop_stop()
    mqtt_service.client.disconnect()

app = FastAPI(
    title="PBL5 Smart Home API",
    description="REST API cho hệ thống nhà thông minh — PBL5 ĐHBK Đà Nẵng",
    version="2.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Socket.IO app
app.mount("/", socketio.ASGIApp(sio, other_asgi_app=app))

# --- Đăng ký tất cả Routers ---
app.include_router(system_routers.router)      # /api/health, /api/time
app.include_router(status_routers.router)       # /api/status/...
app.include_router(sensor_routers.router)       # /api/sensors/...
app.include_router(control_routers.router)      # /api/control/...
app.include_router(schedule_routers.router)     # /api/schedules/...
app.include_router(alarm_routers.router)        # /api/alarms/...
app.include_router(bulk_routers.router)         # /api/bulk/...
app.include_router(weather_routers.router)      # /api/weather/...
app.include_router(context_routers.router)      # /api/context/...
app.include_router(voice_routers.router)        # /api/voice/...

@app.get("/", tags=["Hệ thống"])
def root():
    return {"message": "✅ PBL5 Smart Home Server v2.0 đang hoạt động!"}


# --- Socket.IO Events ---
@sio.event
async def connect(sid, environ):
    print(f"📱 Client {sid} connected to Socket.IO")

@sio.event
async def disconnect(sid):
    print(f"📴 Client {sid} disconnected from Socket.IO")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=SERVER_PORT, reload=True)