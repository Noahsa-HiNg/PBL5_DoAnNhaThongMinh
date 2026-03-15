from fastapi import APIRouter, HTTPException
from controllers.DeviceType_controller import DeviceTypeController
from models.schemas import DeviceTypeBase, DeviceTypeResponse

router = APIRouter(prefix="/api/types", tags=["Device Types"])
controller = DeviceTypeController()

@router.get("/")
def get_all_device_types():
    return controller.get_all_device_types()

@router.get("/{type_id}")
def get_device_type_by_id(type_id: int):
    return controller.get_device_type_by_id(type_id)

@router.get("/name/{type_name}")
def get_device_type_by_name(type_name: str):
    return controller.get_device_type_by_name(type_name)

@router.get("/category/{category}")
def get_device_type_by_category(category: str):
    return controller.get_device_type_by_category(category)