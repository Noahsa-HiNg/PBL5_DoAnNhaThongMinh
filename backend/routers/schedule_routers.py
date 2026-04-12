from fastapi import APIRouter, HTTPException
from datetime import datetime, timedelta
from core.database import get_db_connection, get_device_by_id, get_devices_by_type
from models.schemas import ScheduleSetRequest, TimerSetRequest, BatchTimerRequest

router = APIRouter(prefix="/api/schedules", tags=["Hẹn giờ & Lịch trình"])

@router.post("/set")
async def set_schedule(req: ScheduleSetRequest):
    """Đặt hẹn giờ theo thời gian tuyệt đối (ISO 8601)"""
    device = get_device_by_id(req.device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Không tìm thấy thiết bị")
    
    conn = get_db_connection()
    try:
        conn.execute(
            "INSERT INTO schedules (device_id, command, trigger_time) VALUES (?, ?, ?)",
            (req.device_id, req.command, req.time)
        )
        conn.commit()
        
        # Lấy ID vừa tạo
        cursor = conn.execute("SELECT last_insert_rowid()")
        schedule_id = cursor.fetchone()[0]
    finally:
        conn.close()
    
    return {
        "status": "success",
        "message": f"Đã đặt hẹn giờ cho {device['name']} vào lúc {req.time}",
        "data": {
            "schedule_id": schedule_id,
            "device_id": req.device_id,
            "device_name": device["name"],
            "command": req.command,
            "execute_at": req.time,
            "status": "PENDING"
        }
    }

@router.post("/set-timer")
async def set_timer(req: TimerSetRequest):
    """Hẹn giờ sau N phút kể từ bây giờ"""
    device = get_device_by_id(req.device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Không tìm thấy thiết bị")
    
    trigger_time = (datetime.now() + timedelta(minutes=req.delay_minutes)).strftime("%Y-%m-%d %H:%M:%S")
    
    conn = get_db_connection()
    try:
        conn.execute(
            "INSERT INTO schedules (device_id, command, trigger_time) VALUES (?, ?, ?)",
            (req.device_id, req.command, trigger_time)
        )
        conn.commit()
        cursor = conn.execute("SELECT last_insert_rowid()")
        schedule_id = cursor.fetchone()[0]
    finally:
        conn.close()
    
    return {
        "status": "success",
        "message": f"Đã hẹn giờ {req.command} cho {device['name']} sau {req.delay_minutes} phút",
        "data": {
            "schedule_id": schedule_id,
            "device_id": req.device_id,
            "device_name": device["name"],
            "command": req.command,
            "execute_at": trigger_time,
            "status": "PENDING"
        }
    }

@router.post("/batch")
async def set_batch_timer(req: BatchTimerRequest):
    """Hẹn giờ hàng loạt theo loại thiết bị (light/fan/all)"""
    trigger_time = (datetime.now() + timedelta(minutes=req.delay_minutes)).strftime("%Y-%m-%d %H:%M:%S")
    
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # Lấy danh sách thiết bị theo loại
        if req.device_type == "all":
            cursor.execute("SELECT id, name FROM devices WHERE type IN ('light', 'fan', 'buzzer')")
        else:
            cursor.execute("SELECT id, name FROM devices WHERE type = ?", (req.device_type,))
        
        devices = cursor.fetchall()
        if not devices:
            raise HTTPException(status_code=404, detail="Không tìm thấy thiết bị phù hợp")
        
        schedules = []
        for device in devices:
            cursor.execute(
                "INSERT INTO schedules (device_id, command, trigger_time) VALUES (?, ?, ?)",
                (device["id"], req.command, trigger_time)
            )
            sid = cursor.lastrowid
            schedules.append({
                "schedule_id": sid,
                "device_id": device["id"],
                "device_name": device["name"]
            })
        
        conn.commit()
    finally:
        conn.close()
    
    return {
        "status": "success",
        "message": f"Đã hẹn giờ {req.command} cho {len(schedules)} thiết bị vào lúc {trigger_time}",
        "data": {
            "affected_count": len(schedules),
            "device_type": req.device_type,
            "execute_at": trigger_time,
            "schedules": schedules
        }
    }

@router.get("/active")
async def get_active_schedules():
    """Lấy danh sách hẹn giờ đang chờ (PENDING)"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT s.*, d.name as device_name 
            FROM schedules s 
            LEFT JOIN devices d ON s.device_id = d.id 
            WHERE s.status = 'PENDING' 
            ORDER BY s.trigger_time ASC
        """)
        rows = cursor.fetchall()
    finally:
        conn.close()
    
    schedules = []
    for row in rows:
        schedules.append({
            "schedule_id": row["schedule_id"],
            "device_id": row["device_id"],
            "device_name": row["device_name"],
            "command": row["command"],
            "trigger_time": row["trigger_time"],
            "status": row["status"],
            "created_at": row["created_at"]
        })
    
    return {
        "status": "success",
        "data": {
            "total": len(schedules),
            "schedules": schedules
        }
    }

@router.delete("/cancel-all")
async def cancel_all_schedules():
    """Hủy tất cả hẹn giờ đang chờ"""
    conn = get_db_connection()
    try:
        cursor = conn.execute("UPDATE schedules SET status = 'CANCELLED' WHERE status = 'PENDING'")
        cancelled_count = cursor.rowcount
        conn.commit()
    finally:
        conn.close()
    
    return {
        "status": "success",
        "message": f"Đã hủy {cancelled_count} hẹn giờ đang chờ",
        "data": {"cancelled_count": cancelled_count}
    }

@router.delete("/{schedule_id}")
async def cancel_schedule(schedule_id: int):
    """Hủy 1 hẹn giờ theo ID"""
    conn = get_db_connection()
    try:
        cursor = conn.execute(
            "UPDATE schedules SET status = 'CANCELLED' WHERE schedule_id = ? AND status = 'PENDING'",
            (schedule_id,)
        )
        conn.commit()
    finally:
        conn.close()
    
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="Không tìm thấy hẹn giờ hoặc đã bị hủy")
    
    return {
        "status": "success",
        "message": f"Đã hủy hẹn giờ #{schedule_id}"
    }
