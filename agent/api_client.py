"""
api_client.py — HTTP client gọi FastAPI Smart Home Server
"""

import requests
import logging
from typing import Optional, Dict, Any

from config import API_BASE_URL, API_TIMEOUT, DEVICE_ID_MAP

logger = logging.getLogger(__name__)


class APIError(Exception):
    """Lỗi khi gọi API."""
    def __init__(self, message: str, error_code: str = "", status_code: int = 0):
        super().__init__(message)
        self.error_code  = error_code
        self.status_code = status_code


class SmartHomeAPIClient:
    """
    HTTP client cho REST API Smart Home.
    Tất cả method trả về dict response data khi thành công,
    raise APIError khi server trả error hoặc không kết nối được.
    """

    def __init__(self, base_url: str = API_BASE_URL, timeout: int = API_TIMEOUT):
        self.base_url = base_url.rstrip('/')
        self.timeout  = timeout
        self.session  = requests.Session()
        self.session.headers.update({'Content-Type': 'application/json'})

    # ── Internal helpers ───────────────────────────────────────────────

    def _get(self, path: str, params: Optional[Dict] = None) -> Dict:
        url = f"{self.base_url}{path}"
        try:
            resp = self.session.get(url, params=params, timeout=self.timeout)
            return self._parse(resp)
        except requests.exceptions.ConnectionError:
            raise APIError(f"Không kết nối được server ({url})", "CONNECTION_ERROR")
        except requests.exceptions.Timeout:
            raise APIError(f"Server không phản hồi sau {self.timeout}s", "TIMEOUT")

    def _post(self, path: str, body: Dict) -> Dict:
        url = f"{self.base_url}{path}"
        try:
            resp = self.session.post(url, json=body, timeout=self.timeout)
            return self._parse(resp)
        except requests.exceptions.ConnectionError:
            raise APIError(f"Không kết nối được server ({url})", "CONNECTION_ERROR")
        except requests.exceptions.Timeout:
            raise APIError(f"Server không phản hồi sau {self.timeout}s", "TIMEOUT")

    def _delete(self, path: str) -> Dict:
        url = f"{self.base_url}{path}"
        try:
            resp = self.session.delete(url, timeout=self.timeout)
            return self._parse(resp)
        except requests.exceptions.ConnectionError:
            raise APIError(f"Không kết nối được server ({url})", "CONNECTION_ERROR")
        except requests.exceptions.Timeout:
            raise APIError(f"Server không phản hồi sau {self.timeout}s", "TIMEOUT")

    @staticmethod
    def _parse(resp: requests.Response) -> Dict:
        try:
            data = resp.json()
        except Exception:
            raise APIError(f"Response không phải JSON (HTTP {resp.status_code})", "PARSE_ERROR", resp.status_code)

        if data.get('status') == 'success':
            return data.get('data', {})

        # Server trả error
        raise APIError(
            data.get('message', 'Unknown error'),
            data.get('error_code', 'UNKNOWN'),
            resp.status_code,
        )

    # ── Device ID lookup ───────────────────────────────────────────────

    def get_device_id(self, device_type: str, room: Optional[str]) -> int:
        """
        Tra cứu device_id từ (device_type, room).
        Raise APIError nếu không tìm thấy.
        """
        key = (device_type, room)
        device_id = DEVICE_ID_MAP.get(key)
        if device_id is None:
            raise APIError(
                f"Không tìm thấy device_id cho ({device_type}, {room})",
                "DEVICE_NOT_FOUND",
            )
        return device_id

    # ── 1. Health check ────────────────────────────────────────────────

    def health_check(self) -> Dict:
        """GET /api/health"""
        return self._get('/api/health')

    # ── 2. Điều khiển Đèn (Light) ─────────────────────────────────────

    def control_light(self, device_id: int, state: str) -> Dict:
        """
        POST /api/control/light/{device_id}
        state: 'on' | 'off'
        """
        return self._post(f'/api/control/light/{device_id}', {'state': state})

    def control_light_all(self, state: str) -> Dict:
        """POST /api/control/light/all"""
        return self._post('/api/control/light/all', {'state': state})

    # ── 3. Điều khiển Quạt (Fan) ──────────────────────────────────────

    def control_fan(self, device_id: int, state: str, speed: Optional[int] = None) -> Dict:
        """
        POST /api/control/fan/{device_id}
        state: 'on' | 'off'
        speed: 0–3 (optional, mặc định server tự chọn)
        """
        body: Dict[str, Any] = {'state': state}
        if speed is not None:
            body['speed'] = speed
        return self._post(f'/api/control/fan/{device_id}', body)

    def adjust_fan(self, device_id: int, action: str) -> Dict:
        """
        POST /api/control/fan/{device_id}/adjust
        action: 'up' | 'down'
        """
        return self._post(f'/api/control/fan/{device_id}/adjust', {'action': action})

    # ── 4. Khóa Cửa (Door Lock) ───────────────────────────────────────

    def control_door(self, device_id: int, action: str) -> Dict:
        """
        POST /api/control/door/{device_id}
        action: 'lock' | 'unlock'
        """
        return self._post(f'/api/control/door/{device_id}', {'action': action})

    # ── 5. Buzzer ─────────────────────────────────────────────────────

    def control_buzzer(self, device_id: int, state: str) -> Dict:
        """
        POST /api/control/buzzer/{device_id}
        state: 'on' | 'off'
        """
        return self._post(f'/api/control/buzzer/{device_id}', {'state': state})

    # ── 6. Cảm biến (Sensors) ─────────────────────────────────────────

    def get_sensor_latest(self, device_id: int) -> Dict:
        """GET /api/sensors/latest/{device_id}"""
        return self._get(f'/api/sensors/latest/{device_id}')

    def get_all_sensors(self) -> Dict:
        """GET /api/sensors/all"""
        return self._get('/api/sensors/all')

    def get_sensor_history(self, device_id: int) -> Dict:
        """GET /api/sensors/history/{device_id}"""
        return self._get(f'/api/sensors/history/{device_id}')

    # ── 7. Trạng thái thiết bị (Status) ──────────────────────────────

    def get_device_status(self, device_id: int) -> Dict:
        """GET /api/status/devices/{device_id}"""
        return self._get(f'/api/status/devices/{device_id}')

    def get_all_devices_status(self) -> Dict:
        """GET /api/status/devices"""
        return self._get('/api/status/devices')

    def get_room_status(self, room_slug: str) -> Dict:
        """GET /api/status/rooms/{room_slug}"""
        return self._get(f'/api/status/rooms/{room_slug}')

    def get_door_status(self) -> Dict:
        """GET /api/status/door"""
        return self._get('/api/status/door')

    # ── 8. Thời gian ──────────────────────────────────────────────────

    def get_time(self) -> Dict:
        """GET /api/time"""
        return self._get('/api/time')

    # ── 9. Thời tiết ──────────────────────────────────────────────────

    def get_weather(self, city: str = "Da Nang") -> Dict:
        """GET /api/weather/current?city=..."""
        return self._get('/api/weather/current', params={'city': city})

    # ── 10. Hẹn giờ (Schedules) ───────────────────────────────────────

    def set_schedule(self, payload: Dict) -> Dict:
        """POST /api/schedules/set"""
        return self._post('/api/schedules/set', payload)

    def set_timer(self, payload: Dict) -> Dict:
        """POST /api/schedules/set-timer"""
        return self._post('/api/schedules/set-timer', payload)

    def cancel_schedule(self, schedule_id: str) -> Dict:
        """DELETE /api/schedules/{schedule_id}"""
        return self._delete(f'/api/schedules/{schedule_id}')

    def cancel_all_schedules(self) -> Dict:
        """DELETE /api/schedules/cancel-all"""
        return self._delete('/api/schedules/cancel-all')

    def get_active_schedules(self) -> Dict:
        """GET /api/schedules/active"""
        return self._get('/api/schedules/active')

    # ── 11. Báo thức (Alarms) ─────────────────────────────────────────

    def set_alarm(self, payload: Dict) -> Dict:
        """POST /api/alarms/set"""
        return self._post('/api/alarms/set', payload)

    def cancel_alarm(self, alarm_id: str) -> Dict:
        """DELETE /api/alarms/{alarm_id}"""
        return self._delete(f'/api/alarms/{alarm_id}')

    def get_active_alarms(self) -> Dict:
        """GET /api/alarms/active"""
        return self._get('/api/alarms/active')

    # ── 12. Bulk control ──────────────────────────────────────────────

    def bulk_control(self, actions: list) -> Dict:
        """
        POST /api/bulk/control
        actions: [{'device_id': int, 'command': str}, ...]
        """
        return self._post('/api/bulk/control', {'actions': actions})

    def bulk_all(self, state: str) -> Dict:
        """POST /api/bulk/all — bật/tắt toàn bộ thiết bị"""
        return self._post('/api/bulk/all', {'state': state})

    # ── 13. Context suggestions ───────────────────────────────────────

    def get_context_suggestions(self) -> Dict:
        """GET /api/context/suggestions"""
        return self._get('/api/context/suggestions')

    def confirm_suggestion(self, pending_id: str, confirm: bool) -> Dict:
        """POST /api/context/confirm"""
        return self._post('/api/context/confirm', {'pending_id': pending_id, 'confirm': confirm})
