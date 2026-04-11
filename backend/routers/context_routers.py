from fastapi import APIRouter, HTTPException
from core.database import get_latest_sensor_data, get_device_by_id, update_device_status
from services.mqtt_service import mqtt_service
from models.schemas import ContextConfirmRequest
from datetime import datetime
import json

router = APIRouter(prefix="/api/context", tags=["Gợi ý ngữ cảnh"])

# Bộ nhớ tạm cho pending actions (trong production nên dùng Redis)
pending_actions = {}

@router.get("/suggestions")
async def get_suggestions():
    """Phân tích dữ liệu cảm biến + thời gian → gợi ý hành động phù hợp"""
    
    temp_data = get_latest_sensor_data(9)    # DHT11
    light_data = get_latest_sensor_data(10)  # Ánh sáng
    hour = datetime.now().hour
    
    suggestions = []
    context = "normal"
    reason = "Mọi thứ đang ổn"
    pending_id_counter = len(pending_actions) + 1
    
    # Quy tắc 1: Nóng > 30°C → gợi ý bật quạt
    if temp_data and temp_data["value1"] > 30:
        context = "hot"
        reason = f"Nhiệt độ phòng đang {temp_data['value1']}°C, cao hơn ngưỡng thoải mái"
        pid = f"pending_{pending_id_counter:03d}"
        pending_id_counter += 1
        suggestion = {
            "pending_id": pid,
            "device_id": 5,
            "device_name": "Quạt Phòng Khách",
            "action": "ON",
            "detail": "Bật quạt tốc độ 3",
            "command": json.dumps({"speed": 3})
        }
        suggestions.append(suggestion)
        pending_actions[pid] = suggestion
    
    # Quy tắc 2: Tối (ánh sáng < 100) và buổi tối → gợi ý bật đèn
    if light_data and light_data["value1"] < 100 and hour >= 17:
        context = "dark"
        reason = f"Ánh sáng yếu ({light_data['value1']} lux) vào buổi tối"
        pid = f"pending_{pending_id_counter:03d}"
        pending_id_counter += 1
        suggestion = {
            "pending_id": pid,
            "device_id": 1,
            "device_name": "Đèn Phòng Khách",
            "action": "ON",
            "detail": "Bật đèn phòng khách",
            "command": "ON"
        }
        suggestions.append(suggestion)
        pending_actions[pid] = suggestion
    
    # Quy tắc 3: Khuya > 23h → gợi ý tắt hết
    if hour >= 23:
        context = "sleep"
        reason = "Đã khuya, có thể bạn muốn đi ngủ"
        pid = f"pending_{pending_id_counter:03d}"
        suggestion = {
            "pending_id": pid,
            "device_id": 0,  # 0 = tất cả
            "device_name": "Tất cả thiết bị",
            "action": "OFF",
            "detail": "Tắt tất cả thiết bị",
            "command": "OFF"
        }
        suggestions.append(suggestion)
        pending_actions[pid] = suggestion
    
    return {
        "status": "success",
        "data": {
            "context": context,
            "reason": reason,
            "suggestions": [
                {
                    "pending_id": s["pending_id"],
                    "device_id": s["device_id"],
                    "device_name": s["device_name"],
                    "action": s["action"],
                    "detail": s["detail"]
                } for s in suggestions
            ],
            "expires_in": 60,
            "timestamp": datetime.now().isoformat()
        }
    }

@router.post("/confirm")
async def confirm_suggestion(request: ContextConfirmRequest):
    """Xác nhận hoặc từ chối gợi ý"""
    
    if request.pending_id not in pending_actions:
        raise HTTPException(status_code=404, detail="Gợi ý không tồn tại hoặc đã hết hạn")
    
    action = pending_actions.pop(request.pending_id)
    
    if request.confirm:
        # Thực thi lệnh
        mqtt_service.publish_command(action["device_id"], action["command"])
        if action["device_id"] != 0:
            update_device_status(action["device_id"], action["command"])
        
        return {
            "status": "success",
            "message": f"Đã thực thi: {action['detail']}",
            "data": {
                "pending_id": request.pending_id,
                "executed": True
            }
        }
    else:
        return {
            "status": "success",
            "message": "Đã bỏ qua gợi ý",
            "data": {
                "pending_id": request.pending_id,
                "executed": False,
                "status": "cancelled"
            }
        }
