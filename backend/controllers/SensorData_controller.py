from models.schemas import SensorDataInput
from repositories.SensorData_repo import SensorDataRepo

class SensorDataController:
    def __init__(self):
        self.repo = SensorDataRepo()
        
    def add_sensor_data(self, data: SensorDataInput):
        result = self.repo.add_sensor_data(data)
        if result.get("error"):
            return result
        return result
        
    def get_sensor_history(self, device_id: int = None, limit: int = 50):
        return self.repo.get_sensor_history(device_id, limit)
