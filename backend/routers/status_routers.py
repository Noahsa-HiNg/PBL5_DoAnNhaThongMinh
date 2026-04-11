from fastapi import APIRouter, HTTPException
from core.database import get_db_connection, get_device_by_id, get_devices_by_room, get_room_by_slug

router = APIRouter(prefix="/api/status", tags=["Trạng Thái Thiết Bị"])

# --- ① Route CỐ ĐỊNH phải khai báo TRƯỚC route có {biến} ---

@router.get("/door")
def get_door_status():
    """Lấy trạng thái khóa cửa (device_id = 11)"""
    door = get_device_by_id(11)
    if not door:
        raise HTTPException(status_code=404, detail="Không tìm thấy cửa")
    return {
        "status": "success",
        "data": {
            "device_id": door["id"],
            "name": door["name"],
            "state": door["status"],
        }
    }

@router.get("/rooms/{room_slug}")
def get_room_status(room_slug: str):
    """Lấy tất cả thiết bị trong 1 phòng theo slug (living_room, bedroom, kitchen, yard)"""
    room = get_room_by_slug(room_slug)
    if not room:
        raise HTTPException(status_code=404, detail=f"Phòng '{room_slug}' không tồn tại")
    
    devices = get_devices_by_room(room["id"])
    return {
        "status": "success",
        "data": {
            "room": room["name"],
            "slug": room["slug"],
            "devices": [
                {
                    "device_id": d["id"],
                    "name": d["name"],
                    "type": d["type"],
                    "state": d["status"]
                } for d in devices
            ]
        }
    }

@router.get("/devices")
def list_all_devices():
    """Lấy trạng thái tất cả thiết bị"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM devices")
    devices = cursor.fetchall()
    conn.close()
    
    result = []
    for d in devices:
        result.append({
            "device_id": d["id"],
            "room_id": d["room_id"],
            "name": d["name"],
            "type": d["type"],
            "pin": d["pin"],
            "state": d["status"]
        })
    return {
        "status": "success",
        "data": {
            "devices": result
        }
    }

# --- ② Route có {biến} khai báo SAU cùng ---

@router.get("/devices/{device_id}")
def get_device_status(device_id: int):
    """Lấy trạng thái 1 thiết bị theo ID"""
    device = get_device_by_id(device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Không tìm thấy thiết bị")
    return {
        "status": "success",
        "data": {
            "device_id": device["id"],
            "room_id": device["room_id"],
            "name": device["name"],
            "type": device["type"],
            "state": device["status"]
        }
    }