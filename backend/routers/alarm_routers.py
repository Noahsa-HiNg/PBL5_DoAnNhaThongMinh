from fastapi import APIRouter, HTTPException
from datetime import datetime, timedelta
from uuid import uuid4
from core.database import get_db_connection
from models.schemas import AlarmSetRequest

router = APIRouter(prefix="/api/alarms", tags=["Báo thức"])

@router.post("/set")
async def set_alarm(req: AlarmSetRequest):
    """Đặt báo thức — time: 'HH:MM', repeat: true/false, label: optional"""
    
    # Tạo alarm_id duy nhất
    alarm_id = f"alarm_{uuid4().hex[:6]}"
    
    # Tính next_trigger: hôm nay nếu chưa qua giờ, ngày mai nếu đã qua
    now = datetime.now()
    try:
        h, m = map(int, req.time.split(":"))
        trigger = now.replace(hour=h, minute=m, second=0, microsecond=0)
        if trigger <= now:
            trigger += timedelta(days=1)
    except ValueError:
        raise HTTPException(status_code=400, detail="Định dạng thời gian phải là HH:MM")
    
    conn = get_db_connection()
    try:
        conn.execute(
            "INSERT INTO alarms (alarm_id, time, repeat, label) VALUES (?, ?, ?, ?)",
            (alarm_id, req.time, req.repeat, req.label)
        )
        conn.commit()
    finally:
        conn.close()
    
    return {
        "status": "success",
        "message": f"Đã đặt báo thức lúc {req.time}",
        "data": {
            "alarm_id": alarm_id,
            "time": req.time,
            "repeat": req.repeat,
            "label": req.label,
            "next_trigger": trigger.isoformat(),
            "status": "active"
        }
    }

@router.get("/active")
async def get_active_alarms():
    """Lấy danh sách báo thức đang bật"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM alarms WHERE status = 'active' ORDER BY time ASC")
        rows = cursor.fetchall()
    finally:
        conn.close()
    
    alarms = []
    now = datetime.now()
    for row in rows:
        # Tính next_trigger
        h, m = map(int, row["time"].split(":"))
        trigger = now.replace(hour=h, minute=m, second=0, microsecond=0)
        if trigger <= now:
            trigger += timedelta(days=1)
        
        alarms.append({
            "alarm_id": row["alarm_id"],
            "time": row["time"],
            "repeat": bool(row["repeat"]),
            "label": row["label"],
            "next_trigger": trigger.isoformat(),
            "status": row["status"]
        })
    
    return {
        "status": "success",
        "data": {"alarms": alarms}
    }

@router.delete("/{alarm_id}")
async def cancel_alarm(alarm_id: str):
    """Hủy 1 báo thức"""
    conn = get_db_connection()
    try:
        cursor = conn.execute(
            "UPDATE alarms SET status = 'cancelled' WHERE alarm_id = ? AND status = 'active'",
            (alarm_id,)
        )
        conn.commit()
    finally:
        conn.close()
    
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="Không tìm thấy báo thức hoặc đã bị hủy")
    
    return {
        "status": "success",
        "message": f"Đã hủy báo thức {alarm_id}",
        "data": {"alarm_id": alarm_id, "status": "cancelled"}
    }
