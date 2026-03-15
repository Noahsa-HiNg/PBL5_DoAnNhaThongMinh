from repositories.room_repo import RoomRepo
from models.schemas import RoomBase

class RoomController:
    def __init__(self):
        self.repo = RoomRepo()

    def add_new_room(self, room_data: RoomBase):
        result = self.repo.create_room(room_data)

        if result.get("error"):
            return {"error": "Tên phòng này đã tồn tại trong hệ thống!"}
        
        return result
    def get_all_rooms(self):
        return self.repo.get_all_rooms()
    def delete_room(self, room_id: int):
        return self.repo.delete_room(room_id)

    def update_room(self, room_id: int, room: RoomBase):
        return self.repo.update_room(room_id, room)