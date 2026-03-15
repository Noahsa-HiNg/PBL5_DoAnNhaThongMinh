from fastapi import APIRouter, HTTPException, Query
from models.schemas import SensorDataInput, SensorHistoryResponse
from controllers.SensorData_controller import SensorDataController
from typing import List, Optional

router = APIRouter(prefix="/api/sensors", tags=["Sensor Data"])
controller = SensorDataController()

@router.post("/data")
def receive_sensor_data(data: SensorDataInput):
    result = controller.add_sensor_data(data)
    if result.get("error"):
        raise HTTPException(status_code=400, detail=result["error"])
    return result

@router.get("/history", response_model=List[SensorHistoryResponse])
def get_sensor_history(
    device_id: Optional[int] = Query(None, description="ID của thiết bị cảm biến (tùy chọn)"),
    limit: int = Query(50, description="Giới hạn số bản ghi trả về (mặc định 50, tối đa 100)", le=100)
):
    return controller.get_sensor_history(device_id, limit)
