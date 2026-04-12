from fastapi import APIRouter, HTTPException
from core.database import get_db_connection, get_device_by_id, update_device_status
from services.mqtt_service import mqtt_service
from models.schemas import BulkControlRequest, BulkAllRequest
from datetime import datetime
import json

router = APIRouter(prefix="/api/bulk", tags=["Điều khiển hàng loạt"])

@router.post("/control")
async def bulk_control(request: BulkControlRequest):
    """Điều khiển nhiều thiết bị cùng lúc trong 1 request"""
    
    success = []
    failed = []
    
    for action in request.actions:
        device = get_device_by_id(action.device_id)
        if not device:
            failed.append({
                "device_id": action.device_id,
                "reason": "DEVICE_NOT_FOUND"
            })
            continue
        
        # Gửi MQTT + cập nhật DB
        mqtt_service.publish_command(action.device_id, action.command)
        update_device_status(action.device_id, action.command)
        success.append({
            "device_id": action.device_id,
            "name": device["name"],
            "command": action.command
        })
    
    return {
        "status": "success",
        "message": f"Đã thực thi {len(success)} lệnh, {len(failed)} lỗi",
        "data": {
            "success": success,
            "failed": failed,
            "timestamp": datetime.now().isoformat()
        }
    }

@router.post("/all")
async def control_all_devices(request: BulkAllRequest):
    """Bật/tắt TẤT CẢ thiết bị (trừ cảm biến và cửa)"""
    state = request.state.upper()
    if state not in ["ON", "OFF"]:
        raise HTTPException(status_code=400, detail="state chỉ được là 'on' hoặc 'off'")
    
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # Lấy tất cả thiết bị điều khiển được (trừ sensor và door_lock)
        cursor.execute("SELECT id, name, type FROM devices WHERE type IN ('light', 'fan', 'buzzer')")
        devices = cursor.fetchall()
        
        affected = []
        for d in devices:
            # Tính status phù hợp theo loại thiết bị
            if d["type"] == "fan":
                new_status = "0" if state == "OFF" else "2"  # Quạt: tắt=0, bật=mức 2
                payload = json.dumps({"speed": int(new_status)})
            else:
                new_status = state.lower()  # Đèn, loa: on/off
                payload = state
            
            conn.execute("UPDATE devices SET status = ? WHERE id = ?", (new_status, d["id"]))
            mqtt_service.publish_command(d["id"], payload)
            affected.append(d["name"])
        
        conn.commit()
    finally:
        conn.close()
    
    return {
        "status": "success",
        "message": f"Đã {'bật' if state == 'ON' else 'tắt'} tất cả thiết bị",
        "data": {
            "affected_devices": affected,
            "excluded": ["Cửa Chính", "Cảm biến Nhiệt ẩm", "Cảm biến Ánh sáng"],
            "timestamp": datetime.now().isoformat()
        }
    }
