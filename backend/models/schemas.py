from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime

# ==========================================
# 1. MODELS CHO PHÒNG (ROOMS)
# ==========================================
class RoomBase(BaseModel):
    name: str

class RoomResponse(RoomBase):
    id: int
    
    # Cho phép chuyển đổi trực tiếp từ dữ liệu SQL sang Object Pydantic
    model_config = ConfigDict(from_attributes=True)

# ==========================================
# 2. MODELS CHO LOẠI THIẾT BỊ (DEVICE TYPES)
# ==========================================
class DeviceTypeBase(BaseModel):
    type_name: str
    unit: Optional[str] = None
    category: str  # Chỉ nhận 'sensor' hoặc 'actuator'

class DeviceTypeResponse(DeviceTypeBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

# ==========================================
# 3. MODELS CHO ESP NODES
# ==========================================
class EspNodeBase(BaseModel):
    mac_address: str
    location_desc: Optional[str] = None

class EspNodeResponse(EspNodeBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

# ==========================================
# 4. MODELS CHO THIẾT BỊ (DEVICES)
# ==========================================
# Dùng khi muốn Thêm 1 thiết bị mới từ Web
class DeviceCreate(BaseModel):
    name: str
    room_id: int
    type_id: int
    esp_id: int
    pin: int

# Dùng khi trả danh sách thiết bị về cho Web (Có ID)
class DeviceResponse(DeviceCreate):
    id: int
    model_config = ConfigDict(from_attributes=True)

class DeviceUpdate(BaseModel):
    name: Optional[str] = None
    room_id: Optional[int] = None
    pin: Optional[int] = None

# --- MODEL ĐẶC BIỆT DÀNH CHO FRONTEND ---
# Khi Web hiển thị, nó cần Tên phòng chứ không cần Số ID của phòng
class DeviceDetailResponse(BaseModel):
    id: int
    name: str
    pin: int
    room_name: str      # Tên phòng (Phòng Khách)
    type_name: str      # Loại (RELAY_LIGHT)
    category: str       # actuator/sensor
    mac_address: str    # Của con ESP nào

# ==========================================
# 5. MODELS CHO DỮ LIỆU HOẠT ĐỘNG (LỊCH SỬ & TRẠNG THÁI)
# ==========================================
# Khi ESP32 gửi nhiệt độ lên
class SensorDataInput(BaseModel):
    device_id: int
    value: float

# Khi Web muốn xem lịch sử nhiệt độ
class SensorHistoryResponse(SensorDataInput):
    id: int
    timestamp: datetime
    model_config = ConfigDict(from_attributes=True)

# Khi Web muốn xem trạng thái Đèn đang Bật hay Tắt
class DeviceStatusResponse(BaseModel):
    device_id: int
    status: str
    last_changed: datetime
    model_config = ConfigDict(from_attributes=True)