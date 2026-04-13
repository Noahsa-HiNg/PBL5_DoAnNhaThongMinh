from api_client import SmartHomeAPIClient
from config import SENSOR_TEMP_HUMI_ID
api = SmartHomeAPIClient()
data = api.get_sensor_latest(SENSOR_TEMP_HUMI_ID)
print('Raw data:', data)
print('Keys:', list(data.keys()))