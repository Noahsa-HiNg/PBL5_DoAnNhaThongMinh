from fastapi import APIRouter, HTTPException
from datetime import datetime, timedelta
from core.database import get_db_connection, get_device_by_id, get_devices_by_type, get_id_by_name
from models.schemas import ScheduleSetRequest, TimerSetRequest, BatchTimerRequest, SetByNameRequest, SetTimerByNameRequest
from core.ws_manager import socketio_manager

router = APIRouter(prefix="/api/schedules", tags=["Hen gio & Lich trinh"])

@router.post("/set")
async def set_schedule(req: ScheduleSetRequest):
    """Dat hen gio tuyet doi (ISO 8601)"""
    device = get_device_by_id(req.device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Khong tim thay thiet bi")
    
    conn = get_db_connection()
    try:
        conn.execute(
            "INSERT INTO schedules (device_id, command, trigger_time) VALUES (?, ?, ?)",
            (req.device_id, req.command, req.time)
        )
        conn.commit()
        cursor = conn.execute("SELECT last_insert_rowid()")
        schedule_id = cursor.fetchone()[0]
    finally:
        conn.close()
    
    return {
        "status": "success",
        "message": f"Da dat hen gio cho {device['name']} vao luc {req.time}",
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
    """Hen gio sau N phut ke tu bay gio"""
    device = get_device_by_id(req.device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Khong tim thay thiet bi")
    
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
        "message": f"Da hen gio {req.command} cho {device['name']} sau {req.delay_minutes} phut",
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
    """Hen gio hang loat theo loai thiet bi (light/fan/all)"""
    trigger_time = (datetime.now() + timedelta(minutes=req.delay_minutes)).strftime("%Y-%m-%d %H:%M:%S")
    
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        if req.device_type == "all":
            cursor.execute("SELECT id, name FROM devices WHERE type IN ('light', 'fan', 'buzzer')")
        else:
            cursor.execute("SELECT id, name FROM devices WHERE type = ?", (req.device_type,))
        
        devices = cursor.fetchall()
        if not devices:
            raise HTTPException(status_code=404, detail="Khong tim thay thiet bi phu hop")
        
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
        "message": f"Da hen gio {req.command} cho {len(schedules)} thiet bi vao luc {trigger_time}",
        "data": {
            "affected_count": len(schedules),
            "device_type": req.device_type,
            "execute_at": trigger_time,
            "schedules": schedules
        }
    }

@router.get("/active")
async def get_active_schedules():
    """Lay danh sach hen gio dang cho (PENDING)"""
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
    """Huy tat ca hen gio dang cho"""
    conn = get_db_connection()
    try:
        cursor = conn.execute("UPDATE schedules SET status = 'CANCELLED' WHERE status = 'PENDING'")
        cancelled_count = cursor.rowcount
        conn.commit()
    finally:
        conn.close()
    
    return {
        "status": "success",
        "message": f"Da huy {cancelled_count} hen gio dang cho",
        "data": {"cancelled_count": cancelled_count}
    }

@router.delete("/{schedule_id}")
async def cancel_schedule(schedule_id: int):
    """Huy 1 hen gio theo ID"""
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
        raise HTTPException(status_code=404, detail="Khong tim thay hen gio hoac da bi huy")
    
    return {
        "status": "success",
        "message": f"Da huy hen gio #{schedule_id}"
    }

# ============================================================
# API MOI CHO ANDROID APP (dung device_name thay vi device_id)
# ============================================================

@router.get("/devices")
async def get_devices_for_schedule():
    """Lay danh sach thiet bi de hien thi dropdown tren App"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, type FROM devices WHERE type IN ('light', 'fan', 'buzzer') ORDER BY type, id")
        rows = cursor.fetchall()
    finally:
        conn.close()
    
    devices = [{"device_id": r["id"], "device_name": r["name"], "device_type": r["type"]} for r in rows]
    
    return {
        "status": "success",
        "data": {"devices": devices}
    }

@router.post("/set-by-name")
async def set_schedule_by_name(req: SetByNameRequest):
    """Dat hen gio tuyet doi theo ten thiet bi"""
    device_id = get_id_by_name(req.device_name)
    if not device_id:
        raise HTTPException(status_code=404, detail=f"Khong tim thay thiet bi: {req.device_name}")
    
    device = get_device_by_id(device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Khong tim thay thiet bi")
    
    conn = get_db_connection()
    try:
        conn.execute(
            "INSERT INTO schedules (device_id, command, trigger_time) VALUES (?, ?, ?)",
            (device_id, req.command, req.time)
        )
        conn.commit()
        cursor = conn.execute("SELECT last_insert_rowid()")
        schedule_id = cursor.fetchone()[0]
    finally:
        conn.close()
    
    await socketio_manager.broadcast_schedule_updated(
        action="create",
        schedule_id=schedule_id,
        device_name=req.device_name,
        command=req.command,
        execute_at=req.time
    )
    
    return {
        "status": "success",
        "message": f"Da dat hen gio cho {req.device_name} vao luc {req.time}",
        "data": {
            "schedule_id": schedule_id,
            "device_id": device_id,
            "device_name": req.device_name,
            "command": req.command,
            "execute_at": req.time,
            "status": "PENDING"
        }
    }

@router.post("/set-timer-by-name")
async def set_timer_by_name(req: SetTimerByNameRequest):
    """Hen gio sau N phut theo ten thiet bi"""
    device_id = get_id_by_name(req.device_name)
    if not device_id:
        raise HTTPException(status_code=404, detail=f"Khong tim thay thiet bi: {req.device_name}")
    
    device = get_device_by_id(device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Khong tim thay thiet bi")
    
    trigger_time = (datetime.now() + timedelta(minutes=req.delay_minutes)).strftime("%Y-%m-%d %H:%M:%S")
    
    conn = get_db_connection()
    try:
        conn.execute(
            "INSERT INTO schedules (device_id, command, trigger_time) VALUES (?, ?, ?)",
            (device_id, req.command, trigger_time)
        )
        conn.commit()
        cursor = conn.execute("SELECT last_insert_rowid()")
        schedule_id = cursor.fetchone()[0]
    finally:
        conn.close()
    
    await socketio_manager.broadcast_schedule_updated(
        action="create",
        schedule_id=schedule_id,
        device_name=req.device_name,
        command=req.command,
        execute_at=trigger_time
    )
    
    return {
        "status": "success",
        "message": f"Da hen gio {req.command} cho {req.device_name} sau {req.delay_minutes} phut",
        "data": {
            "schedule_id": schedule_id,
            "device_id": device_id,
            "device_name": req.device_name,
            "command": req.command,
            "execute_at": trigger_time,
            "status": "PENDING"
        }
    }