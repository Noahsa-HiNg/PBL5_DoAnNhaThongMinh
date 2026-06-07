from pydantic import BaseModel, model_validator
from typing import Optional

# ---- CONTROL SCHEMAS ----
class LightControlRequest(BaseModel):
    state: str          # "on" / "off"

class FanControlRequest(BaseModel):
    state: str          # "on" / "off"
    speed: Optional[int] = None  # 0-3, mặc định 2 khi on

class FanAdjustRequest(BaseModel):
    action: str         # "up" / "down"

class DoorControlRequest(BaseModel):
    action: str         # "lock" / "unlock"

class BuzzerControlRequest(BaseModel):
    state: str          # "on" / "off"

class AutoModeRequest(BaseModel):
    command: str        # "ON" / "OFF"

# ---- SCHEDULE SCHEMAS ----
class ScheduleSetRequest(BaseModel):
    device_id: Optional[int] = None       # Voice gui ID
    device_name: Optional[str] = None     # App gui ten
    command: str
    time: str                             # ISO 8601
    
    @model_validator(mode="after")
    def check_device(self):
        if self.device_id is None and self.device_name is None:
            raise ValueError("Phai cung cap device_id HOAC device_name")
        return self

class TimerSetRequest(BaseModel):
    device_id: Optional[int] = None       # Voice gui ID
    device_name: Optional[str] = None     # App gui ten
    command: str
    delay_minutes: int
    
    @model_validator(mode="after")
    def check_device(self):
        if self.device_id is None and self.device_name is None:
            raise ValueError("Phai cung cap device_id HOAC device_name")
        return self

class BatchTimerRequest(BaseModel):
    device_type: str    # "light" / "fan" / "all"
    command: str
    delay_minutes: int

# ---- ALARM SCHEMAS ----
class AlarmSetRequest(BaseModel):
    time: str           # "HH:MM"
    repeat: Optional[bool] = False
    label: Optional[str] = None

# ---- BULK SCHEMAS ----
class BulkAction(BaseModel):
    device_id: int
    command: str

class BulkControlRequest(BaseModel):
    actions: list[BulkAction]

class BulkAllRequest(BaseModel):
    state: str          # "on" / "off"

# ---- CONTEXT SCHEMAS ----
class ContextConfirmRequest(BaseModel):
    pending_id: str
    confirm: bool