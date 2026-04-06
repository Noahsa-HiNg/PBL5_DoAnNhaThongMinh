from fastapi import APIRouter
from database import get_db_connection, get_latest_sensor_data,get_id_by_name
from fastapi import HTTPException
router = APIRouter(prefix="/status", tags=["Trạng Thái Thiết Bị"])

@router.get("/")
def get_all_devices():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM devices")
    devices = cursor.fetchall()
    conn.close()
    
    result = []
    for d in devices:
        result.append({
            "id": d["id"],
            "name": d["name"],
            "type": d["type"],
            "pin": d["pin"],
            "status": d["status"]
        })
    return result

@router.get("/latest/{device_id}")
def get_sensor_status(device_id: int):
    """
    API lấy thông số mới nhất của một cảm biến (DHT11 hoặc Ánh sáng)
    """
    data = get_latest_sensor_data(device_id)
    if not data:
        raise HTTPException(status_code=404, detail="Không tìm thấy dữ liệu cho thiết bị này")
    
    # data thường là một dictionary hoặc tuple từ SQLite
    return {
        "device_id": device_id,
        "value1": data["value1"], # Nhiệt độ hoặc Ánh sáng
        "value2": data["value2"], # Độ ẩm (nếu là DHT11)
        "time": data["timestamp"]
    }


@router.get("/{device_name}")
def get_device_status(device_name: str):
    device_id = get_id_by_name(device_name)
    if not device_id:
        raise HTTPException(status_code=404, detail="Không tìm thấy thiết bị")
    return get_sensor_status(device_id)