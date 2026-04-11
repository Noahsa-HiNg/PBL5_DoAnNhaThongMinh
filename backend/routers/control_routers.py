from fastapi import APIRouter, HTTPException
from core.database import get_db_connection, get_device_by_id, update_device_status
from services.mqtt_service import mqtt_service
from models.schemas import (
    LightControlRequest, FanControlRequest, FanAdjustRequest,
    DoorControlRequest, BuzzerControlRequest, AutoModeRequest
)
import json
from datetime import datetime

router = APIRouter(prefix="/api/control", tags=["Điều khiển thiết bị"])

# ============================================================
# ĐÈN (Light) — device_id: 1, 2, 3, 4
# ============================================================

# --- Route cố định "/light/all" phải ĐẶT TRƯỚC "/light/{device_id}" ---
@router.post("/light/all")
def control_all_lights(request: LightControlRequest):
    """Bật/tắt tất cả đèn"""
    state = request.state.upper()  # "ON" hoặc "OFF"
    if state not in ["ON", "OFF"]:
        raise HTTPException(status_code=400, detail="Lệnh đèn chỉ được là ON hoặc OFF")
    
    conn = get_db_connection()
    conn.execute("UPDATE devices SET status = ? WHERE type = 'light'", (state.lower(),))
    conn.commit()
    conn.close()
    
    # Gửi MQTT cho từng đèn (ID 1-4)
    affected = []
    for device_id in range(1, 5):
        mqtt_service.publish_command(device_id, state)
        device = get_device_by_id(device_id)
        if device:
            affected.append({
                "device_id": device_id,
                "name": device["name"],
                "state": state.lower()
            })
    
    return {
        "status": "success",
        "message": f"Đã {'bật' if state == 'ON' else 'tắt'} tất cả đèn",
        "data": {
            "affected_devices": affected,
            "timestamp": datetime.now().isoformat()
        }
    }

@router.post("/light/{device_id}")
def control_light(device_id: int, request: LightControlRequest):
    """Bật/tắt 1 đèn theo ID"""
    state = request.state.upper()
    if state not in ["ON", "OFF"]:
        raise HTTPException(status_code=400, detail="Lệnh đèn chỉ được là ON hoặc OFF")
    
    device = get_device_by_id(device_id)
    if not device or device["type"] != "light":
        raise HTTPException(status_code=404, detail="Không tìm thấy đèn với ID này")
    
    update_device_status(device_id, state.lower())
    mqtt_service.publish_command(device_id, state)
    
    return {
        "status": "success",
        "message": f"Đã gửi lệnh {state} tới {device['name']}",
        "data": {
            "device_id": device_id,
            "name": device["name"],
            "state": state.lower(),
            "timestamp": datetime.now().isoformat()
        }
    }

# ============================================================
# QUẠT (Fan) — device_id: 5, 6, 7, 8
# ============================================================

@router.post("/fan/{device_id}/adjust")
def adjust_fan_speed(device_id: int, request: FanAdjustRequest):
    """Tăng/giảm tốc độ quạt (up/down)"""
    if request.action not in ["up", "down"]:
        raise HTTPException(status_code=400, detail="action chỉ được là 'up' hoặc 'down'")
    
    device = get_device_by_id(device_id)
    if not device or device["type"] != "fan":
        raise HTTPException(status_code=404, detail="Không tìm thấy quạt với ID này")
    
    # Lấy speed hiện tại từ DB
    try:
        current_speed = int(device["status"])
    except (ValueError, TypeError):
        current_speed = 0
    
    # Tăng hoặc giảm, giới hạn 0-3
    if request.action == "up":
        new_speed = min(current_speed + 1, 3)
    else:
        new_speed = max(current_speed - 1, 0)
    
    # Gửi MQTT + cập nhật DB
    payload = json.dumps({"speed": new_speed})
    mqtt_service.publish_command(device_id, payload)
    update_device_status(device_id, str(new_speed))
    
    return {
        "status": "success",
        "message": f"Đã {'tăng' if request.action == 'up' else 'giảm'} tốc {device['name']} lên mức {new_speed}",
        "data": {
            "device_id": device_id,
            "previous_speed": current_speed,
            "new_speed": new_speed,
            "timestamp": datetime.now().isoformat()
        }
    }

@router.post("/fan/{device_id}")
def control_fan(device_id: int, request: FanControlRequest):
    """Điều khiển quạt — state: on/off, speed: 0-3"""
    state = request.state.lower()
    if state not in ["on", "off"]:
        raise HTTPException(status_code=400, detail="state chỉ được là 'on' hoặc 'off'")
    
    device = get_device_by_id(device_id)
    if not device or device["type"] != "fan":
        raise HTTPException(status_code=404, detail="Không tìm thấy quạt với ID này")
    
    # Xác định speed
    if state == "off":
        speed = 0
    else:
        speed = request.speed if request.speed is not None else 2  # Mặc định mức 2
        if speed not in [0, 1, 2, 3]:
            raise HTTPException(status_code=400, detail="Tốc độ quạt chỉ từ 0 đến 3")
    
    # Gửi MQTT
    payload = json.dumps({"speed": speed})
    mqtt_service.publish_command(device_id, payload)
    update_device_status(device_id, str(speed))
    
    return {
        "status": "success",
        "message": f"Đã gửi lệnh cho {device['name']}",
        "data": {
            "device_id": device_id,
            "name": device["name"],
            "state": state,
            "speed": speed,
            "timestamp": datetime.now().isoformat()
        }
    }

# ============================================================
# KHÓA CỬA (Door Lock) — device_id: 11
# ============================================================

@router.post("/door/{device_id}")
def control_door(device_id: int, request: DoorControlRequest):
    """Khóa/mở cửa — action: lock/unlock"""
    if request.action not in ["lock", "unlock"]:
        raise HTTPException(status_code=400, detail="action chỉ được là 'lock' hoặc 'unlock'")
    
    device = get_device_by_id(device_id)
    if not device or device["type"] != "door_lock":
        raise HTTPException(status_code=404, detail="Không tìm thấy cửa với ID này")
    
    # Map: lock → locked, unlock → unlocked
    new_status = "locked" if request.action == "lock" else "unlocked"
    
    update_device_status(device_id, new_status)
    mqtt_service.publish_command(device_id, request.action.upper())
    
    return {
        "status": "success",
        "message": f"Đã {'khóa' if request.action == 'lock' else 'mở'} {device['name']}",
        "data": {
            "device_id": device_id,
            "name": device["name"],
            "state": new_status,
            "timestamp": datetime.now().isoformat()
        }
    }

# ============================================================
# LOA / BUZZER — device_id: 12
# ============================================================

@router.post("/buzzer/{device_id}")
def control_buzzer(device_id: int, request: BuzzerControlRequest):
    """Bật/tắt loa — state: on/off"""
    state = request.state.lower()
    if state not in ["on", "off"]:
        raise HTTPException(status_code=400, detail="state chỉ được là 'on' hoặc 'off'")
    
    device = get_device_by_id(device_id)
    if not device or device["type"] != "buzzer":
        raise HTTPException(status_code=404, detail="Không tìm thấy loa với ID này")
    
    update_device_status(device_id, state)
    mqtt_service.publish_command(device_id, state.upper())
    
    return {
        "status": "success",
        "message": f"Đã {'bật' if state == 'on' else 'tắt'} {device['name']}",
        "data": {
            "device_id": device_id,
            "name": device["name"],
            "state": state,
            "timestamp": datetime.now().isoformat()
        }
    }

# ============================================================
# CHẾ ĐỘ TỰ ĐỘNG (Auto Mode)
# ============================================================

@router.post("/auto/{type}")
def toggle_auto_mode(type: str, request: AutoModeRequest):
    """Bật/tắt chế độ tự động — type: light/fan/all, command: ON/OFF"""
    command = request.command.upper()
    if command not in ["ON", "OFF"]:
        raise HTTPException(status_code=400, detail="command chỉ được là 'ON' hoặc 'OFF'")
    
    topic = f"home/control/auto/{type}"
    mqtt_service.client.publish(topic, command)
    
    return {
        "status": "success",
        "message": f"Đã {'bật' if command == 'ON' else 'tắt'} chế độ tự động cho {type}",
        "data": {
            "type": type,
            "auto_mode": command,
            "timestamp": datetime.now().isoformat()
        }
    }
