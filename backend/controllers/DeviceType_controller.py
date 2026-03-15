from models.schemas import DeviceTypeBase, DeviceTypeResponse
from repositories.DeviceType_repo import DeviceTypeRepo

class DeviceTypeController:
    def __init__(self):
        self.repo = DeviceTypeRepo()

    def get_all_device_types(self):
        return self.repo.get_all_device_types()

    def get_device_type_by_id(self, type_id: int):
        return self.repo.get_device_type_by_id(type_id)

    def get_device_type_by_name(self, type_name: str):
        return self.repo.get_device_type_by_name(type_name)

    def get_device_type_by_category(self, category: str):
        return self.repo.get_device_type_by_category(category)