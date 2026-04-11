from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import datetime, timedelta
from database import get_db_connection

router = APIRouter(prefix="/api/schedules", tags=["Hẹn giờ & Báo thức"])

# --- SCHEMAS ---
class AlarmRequest(BaseModel):
    device_id: int
    command: str
    time: str

class TimerRequest(BaseModel):
    device_id: int
    command: str
    delay_minutes: int

class AllDevicesTimerRequest(BaseModel):
    device_type: str        # "light", "fan", hoặc "all"
    command: str            # "ON" hoặc "OFF" (hoặc JSON của quạt)
    delay_minutes: int

# --- API BÁO THỨC & HẸN GIỜ ---
@router.post("/set-alarm") #hẹn giờ
async def set_alarm(req: AlarmRequest):
    conn = get_db_connection()
    conn.execute(
        "INSERT INTO schedules (device_id, command, trigger_time) VALUES (?, ?, ?)",
        (req.device_id, req.command, req.time)
    )
    conn.commit()
    conn.close()
    return {"message": f"Đã đặt báo thức cho thiết bị {req.device_id} vào lúc {req.time}"}

@router.post("/set-timer") #hẹn giờ sau 1 khoảng thời gian
async def set_timer(req: TimerRequest):
    trigger_time = (datetime.now() + timedelta(minutes=req.delay_minutes)).strftime("%Y-%m-%d %H:%M:%S")
    conn = get_db_connection()
    conn.execute(
        "INSERT INTO schedules (device_id, command, trigger_time) VALUES (?, ?, ?)",
        (req.device_id, req.command, trigger_time)
    )
    conn.commit()
    conn.close()
    return {"message": f"Đã hẹn giờ sau {req.delay_minutes} phút ({trigger_time})"}

@router.post("/timer-batch") #hẹn giờ tất cả thiết bị
async def set_batch_timer(req: AllDevicesTimerRequest):
    conn = get_db_connection()
    cursor = conn.cursor()
    trigger_time = (datetime.now() + timedelta(minutes=req.delay_minutes)).strftime("%Y-%m-%d %H:%M:%S")
    
    query = "SELECT id FROM devices"
    params = []
    if req.device_type != "all":
        query += " WHERE type = ?"
        params.append(req.device_type)
        
    cursor.execute(query, params)
    devices = cursor.fetchall()
    
    if not devices:
        conn.close()
        return {"error": "Không tìm thấy thiết bị phù hợp"}

    for device in devices:
        did = device['id']
        final_cmd = req.command
        if req.device_type == "fan" and req.command == "OFF":
            final_cmd = '0 - OFF' 
            
        cursor.execute(
            "INSERT INTO schedules (device_id, command, trigger_time) VALUES (?, ?, ?)",
            (did, final_cmd, trigger_time)
        )
    
    conn.commit()
    conn.close()
    return {"status": "success", "message": f"Đã hẹn giờ {req.command} cho {len(devices)} thiết bị vào lúc {trigger_time}"}

# --- API TRUY VẤN & HỦY BÁO THỨC ---
@router.get("/active")
async def get_active_schedules():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM schedules WHERE status = 'PENDING' ORDER BY trigger_time ASC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

@router.delete("/cancel/{schedule_id}")
async def cancel_schedule(schedule_id: int):
    conn = get_db_connection()
    cursor = conn.execute("UPDATE schedules SET status = 'CANCELLED' WHERE schedule_id = ?", (schedule_id,))
    conn.commit()
    conn.close()
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="Không tìm thấy báo thức này")
    return {"message": "Đã hủy báo thức thành công"}

@router.delete("/cancel-all")
async def cancel_all_schedules():
    conn = get_db_connection()
    cursor = conn.execute("UPDATE schedules SET status = 'CANCELLED' WHERE status = 'PENDING'")
    conn.commit()
    conn.close()
    return {"message": "Đã hủy tất cả báo thức thành công"}

def get_all_id_by_type(device_type: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM devices WHERE type = ?", (device_type,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]
