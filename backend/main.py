from fastapi import FastAPI
from routers import room_router, EspNodeBase_router, DeviceType_router, Devices_routers, SensorData_router

app = FastAPI(title="PBL5 Smart Home API")
app.include_router(room_router.router)
app.include_router(EspNodeBase_router.router)
app.include_router(DeviceType_router.router)
app.include_router(Devices_routers.router)
app.include_router(SensorData_router.router)
@app.get("/")
def read_root():
    return {"message": "Hệ thống Backend Smart Home đang chạy!"}