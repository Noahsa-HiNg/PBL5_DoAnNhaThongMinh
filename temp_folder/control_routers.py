from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import json
from database import get_db_connection
from mqtt_clients import mqtt_service

router = APIRouter(prefix="/api/control", tags=["Điều khiển thiết bị"])

# --- SCHEMAS ---
class LightCommand(BaseModel):
    status: str  

class FanControlRequest(BaseModel):
    speed: int   # Tốc độ: 0, 1, 2, 3
    #swing: str   # Xoay: "ON" hoặc "OFF"

class ControlRequest(BaseModel):
    command: str

# --- API ĐIỀU KHIỂN ĐÈN ---
@router.post("/light/all_light_off")
def turn_off_all_light():
    conn = get_db_connection()
    conn.execute("UPDATE devices SET status = 'OFF' WHERE type = 'light'")
    conn.commit()
    conn.close()
    for i in range(1, 5):
        topic = f"home/control/device/{i}"
        mqtt_service.client.publish(topic, "OFF")
    return {"message": "Đã tắt tất cả đèn"}

@router.post("/light/all_light_on")
def turn_on_all_light():
    conn = get_db_connection()
    conn.execute("UPDATE devices SET status = 'ON' WHERE type = 'light'")
    conn.commit()
    conn.close()
    for i in range(1, 5):
        topic = f"home/control/device/{i}"
        mqtt_service.client.publish(topic, "ON")
    return {"message": "Đã bật tất cả đèn"}

@router.post("/light/{device_id}")
def control_light(device_id: int, command: LightCommand):
    if command.status not in ["ON", "OFF"]:
        raise HTTPException(status_code=400, detail="Lệnh đèn chỉ được là ON hoặc OFF")
    conn = get_db_connection()
    conn.execute("UPDATE devices SET status = ? WHERE id = ?", (command.status, device_id))
    conn.commit()
    conn.close()
    topic = f"home/control/device/{device_id}"
    mqtt_service.client.publish(topic, command.status)
    return {"message": f"Đã gửi lệnh {command.status} tới Đèn số {device_id}"}

# --- API ĐIỀU KHIỂN QUẠT ---
@router.post("/fan/{device_id}")
async def control_fan(device_id: int, request: FanControlRequest):
    if request.speed not in [0, 1, 2, 3]:
        raise HTTPException(status_code=400, detail="Tốc độ chỉ được từ 0 đến 3")
        
    payload = json.dumps({"speed": request.speed})
    topic = f"home/control/device/{device_id}"
    mqtt_service.client.publish(topic, payload) # Đã sửa mqtt_manager thành mqtt_service
    
    status_str = f"{request.speed}"
    conn = get_db_connection()
    conn.execute("UPDATE devices SET status = ? WHERE id = ?", (status_str, device_id))
    conn.commit()
    conn.close()
    return {"status": "success", "message": f"Đã gửi lệnh cho Quạt {device_id}", "saved_status": status_str}

# --- API BẬT TẮT CHẾ ĐỘ TỰ ĐỘNG ---
@router.post("/auto/{type}")
async def toggle_auto_mode(type: str, request: ControlRequest):
    topic = f"home/control/auto/{type}"
    mqtt_service.client.publish(topic, request.command)
    return {"message": f"Đã chuyển chế độ tự động {type} sang {request.command}"}