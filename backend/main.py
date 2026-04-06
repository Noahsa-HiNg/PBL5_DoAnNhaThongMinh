from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn
from workers.worker import alarm_worker, cleanup_worker
from database import init_db
from mqtt_clients import mqtt_service
from routers import status_routers, control_routers, schedule_routers, weather_routers
import asyncio
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 Đang khởi động Smart Home Server...")
    init_db()
    mqtt_service.start()
    asyncio.create_task(alarm_worker())
    asyncio.create_task(cleanup_worker())
    yield

    print("🛑 Đang tắt Server...")
    mqtt_service.client.loop_stop()
    mqtt_service.client.disconnect()

app = FastAPI(
    title = "PBL5 Smart Home API",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(status_routers.router)
app.include_router(control_routers.router)
app.include_router(schedule_routers.router)
app.include_router(weather_routers.router)

@app.get("/", tags=["Hệ thống"])
def root():
    return {"message": "✅ PBL5 Smart Home Server đang hoạt động tốt!"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=5000, reload=True)

"""
api trả thông tin thời tiết hiện tại
api đặt báo thức theo giờ 
api đặt tắt báo thức
api bật tắt thiết bị sau một khoảng thời gian
api kiểm tra trạng thái tất cả thiết bị
"""
