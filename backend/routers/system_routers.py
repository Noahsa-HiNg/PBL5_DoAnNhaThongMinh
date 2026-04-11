from fastapi import APIRouter
from datetime import datetime
from services.mqtt_service import mqtt_service

router = APIRouter(prefix="/api", tags=["Hệ thống"])

@router.get("/health")
def health_check():
    """Kiểm tra server + trạng thái kết nối MQTT"""
    return {
        "status": "success",
        "message": "PBL5 Smart Home Server đang hoạt động tốt!",
        "data": {
            "version": "2.0.0",
            "mqtt_connected": mqtt_service.client.is_connected(),
        }
    }

@router.get("/time")
def get_time():
    now = datetime.now()
    hour = now.hour
    
    if 5 <= hour < 12:
        context = "morning"
    elif 12 <= hour < 18:
        context = "afternoon"
    elif 18 <= hour < 22:
        context = "evening"
    else:
        context = "night"
        
    return {
        "time": now.strftime("%H:%M:%S"),
        "date": now.strftime("%Y-%m-%d"),
        "context": context
    }
