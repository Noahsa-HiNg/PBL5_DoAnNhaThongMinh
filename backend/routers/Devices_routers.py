from fastapi import APIRouter, HTTPException
from controllers.Devices_controller import DeviceController
from models.schemas import DeviceCreate,DeviceResponse,DeviceDetailResponse,DeviceUpdate,DeviceStatusResponse

router = APIRouter(prefix="/api/devices", tags=["Devices"])
controller = DeviceController()

@router.post("/", response_model=DeviceResponse)
def create_device(device: DeviceCreate):
    return controller.add_new_device(device)
@router.get("/", response_model=list[DeviceResponse])
def get_all_devices():
    return controller.get_all_devices()
@router.get("/{device_id}", response_model=DeviceResponse)
def get_device_by_id(device_id: int):
    return controller.get_device_by_id(device_id)
@router.delete("/{device_id}")
def delete_device(device_id: int):
    return controller.delete_device(device_id)
@router.put("/{device_id}", response_model=DeviceResponse)
def update_device(device_id: int, device: DeviceUpdate):
    return controller.update_device(device_id, device)

@router.get("/{device_id}/status", response_model=DeviceStatusResponse)
def get_device_status(device_id: int):
    status = controller.get_device_status(device_id)
    if not status:
        raise HTTPException(status_code=404, detail="Không tìm thấy trạng thái thiết bị")
    return status

from pydantic import BaseModel
class DeviceControlInput(BaseModel):
    status: str

@router.post("/{device_id}/control")
def control_device(device_id: int, command: DeviceControlInput):
    result = controller.control_device(device_id, command.status)
    if result.get("error"):
        raise HTTPException(status_code=400, detail=result["error"])
    return result