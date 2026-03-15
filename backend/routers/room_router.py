from fastapi import APIRouter, HTTPException
from models.schemas import RoomBase, RoomResponse
from controllers.room_controller import RoomController

router = APIRouter(prefix="/api/rooms", tags=["Quản lý Phòng"])

controller = RoomController()

@router.post("/")
def create_room_api(room_in: RoomBase):
    result = controller.add_new_room(room_in)
    if result.get("error"):
        raise HTTPException(status_code=400, detail=result["error"])
    return result
@router.get("/")
def get_all_rooms_api():
    return controller.get_all_rooms()
@router.delete("/{room_id}")
def delete_room_api(room_id: int):
    return controller.delete_room(room_id)

@router.put("/{room_id}")
def update_room_api(room_id: int, room_in: RoomBase):
    return controller.update_room(room_id, room_in)