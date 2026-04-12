"""
dialog_state.py — DialogState dataclass cho Smart Home Dialog Manager
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, List


# Trạng thái mặc định của thiết bị khi khởi động
DEFAULT_DEVICE_STATES: Dict[str, str] = {
    'light_living_room':       'off',
    'light_bedroom':           'off',
    'light_kitchen':           'off',
    'light_yard':              'off',
    'fan_living_room':         'off',
    'fan_bedroom':             'off',
    'fan_kitchen':             'off',
    'ventilation_fan_kitchen': 'off',
    'door_lock':               'locked',
}


@dataclass
class DialogState:
    """
    Lưu trạng thái hội thoại giữa các turn.

    Attributes:
        last_device:      Thiết bị được nhắc đến gần nhất ('light', 'fan', ...)
        last_room:        Phòng được nhắc đến gần nhất ('bedroom', 'living_room', ...)
        last_action:      Action gần nhất ('on', 'off', 'adj_up', ...)
        last_intent:      Intent gần nhất của NLU
        pending_action:   Dict lưu context suggest chờ user xác nhận
                          {'actions': [(device, room, action), ...], 'intent': str}
        pending_ttl:      Số turn còn lại trước khi pending_action hết hạn
        waiting_room:     Dict lưu trạng thái chờ user cung cấp phòng
                          {'action': str, 'device': str, 'act_slot': str,
                           'from_context': bool (optional)}
        waiting_ttl:      Số turn còn lại trước khi waiting_room hết hạn
        last_schedule:    Chuỗi DM output của lần đặt lịch gần nhất
        last_alarm:       Thời gian đặt báo thức gần nhất ('06:30')
        device_states:    Trạng thái nội bộ các thiết bị (mirror local, không
                          query API mỗi lần — dùng để trả lời query_status nhanh)
        history:          Danh sách intent theo thứ tự các turn
    """
    last_device:    Optional[str]       = None
    last_room:      Optional[str]       = None
    last_action:    Optional[str]       = None
    last_intent:    Optional[str]       = None
    pending_action: Optional[Dict]      = None
    pending_ttl:    int                 = 0
    waiting_room:   Optional[Dict]      = None
    waiting_ttl:    int                 = 0
    last_schedule:  Optional[str]       = None
    last_alarm:     Optional[str]       = None
    device_states:  Dict[str, str]      = field(
        default_factory=lambda: dict(DEFAULT_DEVICE_STATES)
    )
    history:        List[str]           = field(default_factory=list)

    def reset(self):
        """Reset toàn bộ state về mặc định."""
        self.last_device    = None
        self.last_room      = None
        self.last_action    = None
        self.last_intent    = None
        self.pending_action = None
        self.pending_ttl    = 0
        self.waiting_room   = None
        self.waiting_ttl    = 0
        self.last_schedule  = None
        self.last_alarm     = None
        self.device_states  = dict(DEFAULT_DEVICE_STATES)
        self.history        = []

    def update_device_state(self, device: str, room: Optional[str], new_state: str):
        """Cập nhật trạng thái thiết bị trong local mirror."""
        if device == 'all' or room == 'all':
            for k in self.device_states:
                if k == 'door_lock':
                    continue
                self.device_states[k] = new_state
            return

        if device == 'door_lock':
            self.device_states['door_lock'] = new_state
        elif device == 'ventilation_fan':
            self.device_states['ventilation_fan_kitchen'] = new_state
        elif room:
            key = f'{device}_{room}'
            if key in self.device_states:
                self.device_states[key] = new_state

    def get_device_state(self, device: str, room: Optional[str]) -> str:
        """Lấy trạng thái thiết bị từ local mirror."""
        if device == 'door_lock':
            return self.device_states.get('door_lock', 'unknown')
        if device == 'ventilation_fan':
            return self.device_states.get('ventilation_fan_kitchen', 'unknown')
        if room:
            return self.device_states.get(f'{device}_{room}', 'unknown')
        return 'unknown'
