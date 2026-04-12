from fastapi import APIRouter, HTTPException
from typing import Optional
from core.database import get_latest_sensor_data, get_sensor_history, get_device_by_id

router = APIRouter(prefix="/api/sensors", tags=["Cảm biến"])

@router.get("/latest/{device_id}")
def get_sensor_latest(device_id: int):
    """Lấy dữ liệu cảm biến mới nhất — device_id: 9 (DHT11) hoặc 10 (Ánh sáng)"""
    
    device = get_device_by_id(device_id)
    if not device or device["type"] != "sensor":
        raise HTTPException(status_code=404, detail="Thiết bị không phải cảm biến")
    
    data = get_latest_sensor_data(device_id)
    if not data:
        raise HTTPException(status_code=404, detail="Chưa có dữ liệu cảm biến")
    
    # Phân biệt DHT11 vs Ánh sáng
    if device_id == 9:  # DHT11
        return {
            "status": "success",
            "data": {
                "device_id": device_id,
                "name": device["name"],
                "type": "dht11",
                "temperature": {"value": data["value1"], "unit": "°C"},
                "humidity": {"value": data["value2"], "unit": "%"},
                "timestamp": data["timestamp"]
            }
        }
    else:  # Ánh sáng (device_id == 10)
        return {
            "status": "success",
            "data": {
                "device_id": device_id,
                "name": device["name"],
                "type": "light_sensor",
                "light": {"value": data["value1"], "unit": "lux"},
                "timestamp": data["timestamp"]
            }
        }

@router.get("/all")
def get_all_sensors():
    """Lấy dữ liệu tất cả cảm biến (DHT11 + Ánh sáng)"""
    
    temp_data = get_latest_sensor_data(9)   # DHT11
    light_data = get_latest_sensor_data(10) # Ánh sáng
    
    result = {}
    timestamp = None
    
    if temp_data:
        result["temperature"] = {"device_id": 9, "value": temp_data["value1"], "unit": "°C"}
        result["humidity"] = {"device_id": 9, "value": temp_data["value2"], "unit": "%"}
        timestamp = temp_data["timestamp"]
    
    if light_data:
        result["light"] = {"device_id": 10, "value": light_data["value1"], "unit": "lux"}
        timestamp = light_data["timestamp"] or timestamp
    
    if not result:
        raise HTTPException(status_code=404, detail="Chưa có dữ liệu cảm biến nào")
    
    result["timestamp"] = timestamp
    return {"status": "success", "data": result}

@router.get("/history/{device_id}")
def get_sensor_history_api(
    device_id: int,
    limit: int = 50,
    from_time: Optional[str] = None,
    to_time: Optional[str] = None
):
    """
    Lấy lịch sử cảm biến.
    - limit: số bản ghi (mặc định 50, tối đa 200)
    - from_time: thời gian bắt đầu (ISO 8601, optional)
    - to_time: thời gian kết thúc (ISO 8601, optional)
    """
    
    device = get_device_by_id(device_id)
    if not device or device["type"] != "sensor":
        raise HTTPException(status_code=404, detail="Thiết bị không phải cảm biến")
    
    # Giới hạn tối đa 200 bản ghi
    limit = min(limit, 200)
    
    records = get_sensor_history(device_id, limit, from_time, to_time)
    
    return {
        "status": "success",
        "data": {
            "device_id": device_id,
            "name": device["name"],
            "total_records": len(records),
            "records": records
        }
    }
