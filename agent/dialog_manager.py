"""
dialog_manager.py — Dialog Manager v9
Port 1:1 từ SmartHome_DialogManager_v9.ipynb Cell 7.
Chỉ thay đổi duy nhất:
  - __init__ nhận thêm api_client
  - _apply_action  → gọi API thật, giữ nguyên return string
  - _handle_query_sensor → gọi API thật thay vì self.sensor
  - _handle_query_time   → gọi API thật, fallback local
  - query_weather        → gọi API thật thay vì 'unavailable'
Toàn bộ logic DM (extract_slots, handlers, TTL, FIX 1-7) giữ nguyên.
"""

from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Tuple
import logging

from api_client import SmartHomeAPIClient, APIError
from config import SENSOR_TEMP_HUMI_ID, SENSOR_LIGHT_ID, DOOR_LOCK_ID

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
#  CONSTANTS  (copy nguyên từ notebook)
# ─────────────────────────────────────────────
MOCK_SENSOR = {'temp': 30, 'hum': 75, 'co2': 850}

DEFAULT_DEVICE_STATES = {
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

MAX_PENDING_TURNS = 3
MAX_WAIT_TURNS    = 2

# [FIX-5v9] Các intent không tick TTL waiting_room/pending_action
NON_TICK_INTENTS = {
    'query_time', 'query_weather', 'query_sensor',
    'query_status', 'chitchat', 'unsupported',
}

ROOM_VI_MAP = {
    'phòng khách':  'living_room',
    'phong khach':  'living_room',
    'khách':        'living_room',
    'khach':        'living_room',
    'phòng ngủ':    'bedroom',
    'phong ngu':    'bedroom',
    'ngủ':          'bedroom',
    'ngu':          'bedroom',
    'phòng bếp':    'kitchen',
    'phong bep':    'kitchen',
    'bếp':          'kitchen',
    'bep':          'kitchen',
    'nhà bếp':      'kitchen',
    'nha bep':      'kitchen',
    'sân':          'yard',
    'san':          'yard',
}

@dataclass
class DialogState:
    last_device:      Optional[str]  = None
    last_room:        Optional[str]  = None
    last_action:      Optional[str]  = None
    last_intent:      Optional[str]  = None
    pending_action:   Optional[Dict] = None
    pending_ttl:      int            = 0
    waiting_room:     Optional[Dict] = None
    waiting_ttl:      int            = 0
    last_schedule:    Optional[str]  = None
    last_alarm:       Optional[str]  = None
    device_states:    Dict[str, str] = field(default_factory=lambda: dict(DEFAULT_DEVICE_STATES))
    history:          List[str]      = field(default_factory=list)

DEVICE_MAP = {
    'device-light':           'light',
    'device-fan':             'fan',
    'device-ventilation_fan': 'ventilation_fan',
    'device-door_lock':       'door_lock',
    'device-all':             'all',
}
ROOM_MAP = {
    'room-living_room': 'living_room',
    'room-bedroom':     'bedroom',
    'room-kitchen':     'kitchen',
    'room-yard':        'yard',
    'room-all':         'all',
}
ACTION_MAP = {
    'action_on-on':        'on',
    'action_on-on_all':    'on',
    'action_off-off':      'off',
    'action_off-off_all':  'off',
    'action_adj-adj_up':   'adj_up',
    'action_adj-adj_down': 'adj_down',
    'action_lock-lock':    'lock',
    'action_lock-unlock':  'unlock',
    'action_check-check':  'check',
}
# [FIX-3v9] Các action slot có variant "_all" → expand tất cả rooms
ACTION_ALL_SLOTS = {'action_on-on_all', 'action_off-off_all'}

ACTION_LABEL = {
    'on':       'bật',
    'off':      'tắt',
    'lock':     'khóa',
    'unlock':   'mở khóa',
    'adj_up':   'tăng',
    'adj_down': 'giảm',
    'check':    'kiểm tra',
}
DEVICE_ROOMS = {
    'light':           ['living_room', 'bedroom', 'kitchen', 'yard'],
    'fan':             ['living_room', 'bedroom', 'kitchen'],
    'ventilation_fan': ['kitchen'],
    'door_lock':       None,
    'all':             None,
}
NO_ROOM_DEVICES = {'door_lock', 'all', 'ventilation_fan'}

# device cần hỏi phòng khi confirm sau context suggest
CONTEXT_SUGGEST_ASK_ROOM = {'fan', 'light'}
# [FIX-2v9] Thêm context_arrive và context_wake — suggest đã có room cố định
CONTEXT_SUGGEST_NO_ASK = {
    'context_cold', 'context_sleep', 'context_leave', 'context_stuffy',
    'context_arrive', 'context_wake',
}

CONTEXT_SUGGEST = {
    'context_hot':    [('fan',             'living_room', 'on')],
    'context_cold':   [('fan',             'living_room', 'off'), ('fan', 'bedroom', 'off')],
    'context_stuffy': [('ventilation_fan', 'kitchen',     'on')],
    'context_sleep':  [('light',           'bedroom',     'off'), ('fan', 'bedroom', 'off')],
    'context_wake':   [('light',           'bedroom',     'on')],
    'context_arrive': [('light',           'living_room', 'on')],
    'context_leave':  [('all',             None,          'off')],
}
INTENT_SIGNAL_MAP = {
    'context_hot':    'signal_hot',
    'context_cold':   'signal_cold',
    'context_stuffy': 'signal_stuffy',
    'context_sleep':  'signal_sleep',
    'context_wake':   'signal_wake',
    'context_arrive': 'signal_arrive',
    'context_leave':  'signal_leave',
}


# ── Helpers (copy nguyên từ notebook) ────────────────────────────────

def _time_context(hour: int) -> str:
    if 5 <= hour < 12:  return 'morning'
    if 12 <= hour < 17: return 'afternoon'
    if 17 <= hour < 21: return 'evening'
    return 'night'


def _device_key(device: str, room: Optional[str]) -> Optional[str]:
    if device == 'door_lock':        return 'door_lock'
    if device == 'ventilation_fan':  return 'ventilation_fan_kitchen'
    if device == 'all' or room == 'all': return 'all'
    if room: return f'{device}_{room}'
    return None


def _apply_action_local(state: DialogState, device: str, room: Optional[str], action: str) -> str:
    """
    Cập nhật local device_states (giống _apply_action notebook).
    Trả về chuỗi kết quả giống hệt notebook.
    """
    if action in ('on', 'off'):
        if device == 'all' or room == 'all':
            for k in state.device_states:
                if k == 'door_lock': continue
                state.device_states[k] = action
            return 'all:' + action
        key = _device_key(device, room)
        if key and key in state.device_states:
            state.device_states[key] = action
            return f'{key}:{action}'
    elif action == 'lock':
        state.device_states['door_lock'] = 'locked'
        return 'door_lock:locked'
    elif action == 'unlock':
        state.device_states['door_lock'] = 'unlocked'
        return 'door_lock:unlocked'
    elif action in ('adj_up', 'adj_down'):
        key = _device_key(device, room)
        if key: return f'{key}:adjusted'
    return 'unknown'


def _extract_action_only(slots: List) -> Optional[Tuple[str, str]]:
    """
    [FIX-1v9] Lấy action đầu tiên từ slots kể cả khi không có device.
    Trả về (action_value, action_slot) hoặc None.
    """
    for _, lbl, _ in slots:
        raw = lbl[2:] if lbl.startswith(('B-', 'I-')) else lbl
        if lbl.startswith('B-') and raw in ACTION_MAP:
            return (ACTION_MAP[raw], raw)
    return None


def _extract_slots(slots: List) -> Tuple:
    """
    Orphan I- → B-  (giữ từ v7)
    action+dev+room1+room2 → nhân bản  (giữ từ v7)
    PatternA/B multi-action/device  (giữ từ v7)
    """
    actions          = []
    signal           = None
    sensor           = None
    time_abs_words   = []
    time_del_words   = []
    value_words      = []
    last_entity_type = None
    current_action   = {}

    def _flush_current(ca: dict) -> list:
        if not ca.get('action'): return []
        devices = ca.get('devices', [])
        if not devices and ca.get('device'): devices = [ca['device']]
        if not devices: return []
        rooms = ca.get('rooms', [])
        if not rooms: rooms = [None]
        return [{'action':      ca['action'],
                 'action_slot': ca.get('action_slot', ''),
                 'is_all':      ca.get('is_all', False),
                 'device':      dev,
                 'room':        rm}
                for dev in devices for rm in rooms]

    for word, lbl, conf in slots:
        raw      = lbl[2:] if lbl.startswith(('B-', 'I-')) else lbl
        is_begin = lbl.startswith('B-')
        is_inner = lbl.startswith('I-')

        # Orphan I- fix
        if is_inner and raw != last_entity_type:
            if raw in ACTION_MAP:
                last_entity_type = raw; continue
            else:
                is_begin = True; is_inner = False

        if raw in ACTION_MAP:
            last_entity_type = raw
            if is_begin:
                actions.extend(_flush_current(current_action))
                # [FIX-3v9] đánh dấu is_all nếu action slot là _all variant
                current_action = {
                    'action':      ACTION_MAP[raw],
                    'action_slot': raw,
                    'is_all':      raw in ACTION_ALL_SLOTS,
                    'devices':     [],
                    'rooms':       [],
                }

        elif raw in DEVICE_MAP:
            last_entity_type = raw
            dev = DEVICE_MAP[raw]
            if is_begin:
                if current_action.get('devices') and current_action.get('rooms'):
                    actions.extend(_flush_current(current_action))
                    current_action = {
                        'action':      current_action['action'],
                        'action_slot': current_action['action_slot'],
                        'is_all':      current_action.get('is_all', False),
                        'devices':     [],
                        'rooms':       [],
                    }
                current_action.setdefault('devices', [])
                current_action['devices'].append(dev)
                if dev in NO_ROOM_DEVICES:
                    room_val = 'kitchen' if dev == 'ventilation_fan' else None
                    current_action.setdefault('rooms', [])
                    if room_val not in current_action['rooms']:
                        current_action['rooms'].append(room_val)

        elif raw in ROOM_MAP:
            last_entity_type = raw
            if is_begin:
                current_action.setdefault('rooms', [])
                current_action['rooms'].append(ROOM_MAP[raw])

        elif raw.startswith('sensor'):
            last_entity_type = raw
            if is_begin: sensor = raw
        elif raw.startswith('signal'):
            last_entity_type = raw
            if is_begin: signal = raw
        elif raw == 'time_absolute':
            last_entity_type = raw; time_abs_words.append(word)
        elif raw == 'time_delay':
            last_entity_type = raw; time_del_words.append(word)
        elif raw == 'value':
            last_entity_type = raw; value_words.append(word)
        else:
            last_entity_type = None

    actions.extend(_flush_current(current_action))

    return (actions, signal, sensor,
            ' '.join(time_abs_words) or None,
            ' '.join(time_del_words) or None,
            ' '.join(value_words)    or None)


def _resolve_room_from_text(raw_text: str) -> Optional[str]:
    text_lower = raw_text.lower().strip()
    for vi, key in sorted(ROOM_VI_MAP.items(), key=lambda x: -len(x[0])):
        if vi in text_lower: return key
    return None


def _get_sensor_level(value, sensor_type: str) -> str:
    if sensor_type == 'sensor-temperature':
        return 'high' if value > 35 else ('low' if value < 18 else 'normal')
    elif sensor_type == 'sensor-humidity':
        return 'high' if value > 80 else ('low' if value < 40 else 'normal')
    elif sensor_type == 'sensor-co2':
        return 'high' if value > 1000 else ('medium' if value > 700 else 'normal')
    return 'normal'


# ── Dialog Manager class ─────────────────────────────────────────────

class SmartHomeDialogManager:

    def __init__(self, api_client: Optional[SmartHomeAPIClient] = None,
                 sensor_data: Optional[Dict] = None):
        self.state  = DialogState()
        self.sensor = sensor_data or dict(MOCK_SENSOR)  # fallback khi không có API
        self.api    = api_client  # None = không gọi API (dùng mock sensor)

    def reset(self):
        self.state = DialogState()

    def process(self, nlu_result: Dict, raw_text: str = '') -> str:
        return self.process_raw(nlu_result, raw_text)

    def process_raw(self, nlu_result: Dict, raw_text: str = '') -> str:
        intent = nlu_result['intent']
        slots  = nlu_result['slots']
        state  = self.state

        state.last_intent = intent
        state.history.append(intent)

        # [FIX-5v9] Tick TTL chỉ khi intent là action/confirm, không tick khi query
        if intent not in NON_TICK_INTENTS:
            if state.pending_action:
                state.pending_ttl -= 1
                if state.pending_ttl <= 0:
                    state.pending_action = None; state.pending_ttl = 0
            if state.waiting_room:
                state.waiting_ttl -= 1
                if state.waiting_ttl <= 0:
                    state.waiting_room = None; state.waiting_ttl = 0

        # ── waiting_room handler ──────────────────────────────────────
        # [FIX-6v9] Xử lý waiting_room TRƯỚC khi dispatch intent
        if state.waiting_room:
            room_from_slots = next(
                (ROOM_MAP[lbl[2:]] for _, lbl, _ in slots
                 if lbl.startswith('B-') and lbl[2:] in ROOM_MAP), None)
            if not room_from_slots and raw_text:
                room_from_slots = _resolve_room_from_text(raw_text)

            if room_from_slots:
                pending_wr = state.waiting_room
                state.waiting_room = None; state.waiting_ttl = 0

                # from_context: resolve pending_action sau context suggest
                if pending_wr.get('from_context') and state.pending_action:
                    pa_actions = state.pending_action.get('actions', [])
                    pa_actions = [(d, room_from_slots if d in CONTEXT_SUGGEST_ASK_ROOM else r, a)
                                  for d, r, a in pa_actions]
                    results = []; detail_parts = []
                    for dev, rm, act in pa_actions:
                        res = self._apply_action(state, dev, rm, act)
                        results.append(res)
                        # [FIX-4v9] Thêm detail cho NLG
                        detail_parts += [
                            f'device-{dev}',
                            f'room-{rm}' if rm else '',
                            f'action_label={ACTION_LABEL.get(act, act)}'
                        ]
                        state.last_device = dev; state.last_room = rm; state.last_action = act
                    state.pending_action = None; state.pending_ttl = 0
                    detail_str = ' | '.join(p for p in detail_parts if p)
                    return f'RESULT:{",".join(results)} | confirm_yes | {detail_str}'

                # from_context=False: resolve đơn lẻ, trả control_device
                result = self._apply_action(state, pending_wr['device'], room_from_slots, pending_wr['action'])
                state.last_device = pending_wr['device']
                state.last_room   = room_from_slots
                state.last_action = pending_wr['action']
                lbl_vi = ACTION_LABEL.get(pending_wr['action'], pending_wr['action'])
                return (f"RESULT:{result} | control_device"
                        f" | {pending_wr['act_slot']}"
                        f" | device-{pending_wr['device']}"
                        f" | room-{room_from_slots}"
                        f" | action_label={lbl_vi}")

            # Không có room → pass qua, giữ waiting_room
        # ─────────────────────────────────────────────────────────────

        if intent == 'control_device':
            return self._handle_control(slots, state)
        elif intent == 'query_status':
            return self._handle_query_status(slots, state)
        elif intent == 'query_sensor':
            return self._handle_query_sensor(slots)
        elif intent == 'query_time':
            return self._handle_query_time()
        elif intent == 'query_weather':
            return self._handle_query_weather()
        elif intent == 'schedule_set':
            return self._handle_schedule(slots, state)
        elif intent == 'schedule_cancel':
            return self._handle_cancel('schedule', state)
        elif intent == 'alarm_set':
            return self._handle_alarm(slots, state, mode='set')
        elif intent == 'alarm_cancel':
            return self._handle_cancel('alarm', state)
        elif intent in ('context_hot', 'context_cold', 'context_stuffy',
                        'context_sleep', 'context_wake',
                        'context_arrive', 'context_leave'):
            return self._handle_context(intent, slots, state)
        elif intent == 'confirm_yes':
            return self._handle_confirm(slots, state, raw_text=raw_text)
        elif intent == 'confirm_no':
            state.pending_action = None; state.pending_ttl = 0
            state.waiting_room   = None; state.waiting_ttl = 0
            return 'RESULT:cancelled | confirm_no'
        elif intent == 'chitchat':
            return 'RESULT:ok | chitchat | question=general'
        else:
            return 'RESULT:unsupported | unsupported'

    # ── API wrapper ───────────────────────────────────────────────────
    # Gọi API thật nếu có api_client, sau đó cập nhật local state
    # Trả về cùng string format với _apply_action_local (không thay đổi DM output)

    def _apply_action(self, state: DialogState, device: str,
                      room: Optional[str], action: str) -> str:
        """
        Cập nhật local state + gọi API thật (nếu có).
        Return string giống hệt _apply_action notebook.
        """
        # 1. Cập nhật local state trước (luôn làm dù API fail)
        result = _apply_action_local(state, device, room, action)

        # 2. Gọi API thật nếu có client
        if self.api is None:
            return result  # chế độ mock (không có server)

        try:
            if device == 'light':
                did = self.api.get_device_id('light', room)
                self.api.control_light(did, action)

            elif device == 'fan':
                did = self.api.get_device_id('fan', room)
                if action in ('on', 'off'):
                    self.api.control_fan(did, action)
                elif action == 'adj_up':
                    self.api.adjust_fan(did, 'up')
                elif action == 'adj_down':
                    self.api.adjust_fan(did, 'down')

            elif device == 'ventilation_fan':
                did = self.api.get_device_id('ventilation_fan', 'kitchen')
                if action in ('on', 'off'):
                    self.api.control_fan(did, action)

            elif device == 'door_lock':
                if action in ('lock', 'unlock'):
                    self.api.control_door(DOOR_LOCK_ID, action)

            elif device == 'all':
                if action in ('on', 'off'):
                    self.api.bulk_all(action)

        except APIError as e:
            logger.warning(f"API call failed [{e.error_code}]: {e} — dùng local state")

        return result  # luôn trả string local (không đổi format DM output)

    # ------------------------------------------------------------------
    def _handle_query_time(self) -> str:
        # Thử gọi API, fallback về local time
        if self.api:
            try:
                data = self.api.get_time()
                hhmm = data.get('time', '')
                ctx  = data.get('context', '')
                return f'RESULT:{hhmm} | query_time | context={ctx}'
            except APIError:
                pass
        now  = datetime.now()
        hhmm = now.strftime('%H:%M')
        ctx  = _time_context(now.hour)
        return f'RESULT:{hhmm} | query_time | context={ctx}'

    # ------------------------------------------------------------------
    def _handle_control(self, slots, state: DialogState) -> str:
        actions_raw, signal, _, time_abs, time_del, value = _extract_slots(slots)
        actions = [a for a in actions_raw if a.get('device')]

        # [FIX-1v9] Khi actions rỗng — lấy action từ NLU trước, KHÔNG dùng last_action
        if not actions:
            nlu_action_info = _extract_action_only(slots)
            if nlu_action_info and state.last_device:
                nlu_act, nlu_act_slot = nlu_action_info
                actions = [{
                    'action':      nlu_act,
                    'action_slot': nlu_act_slot,
                    'is_all':      nlu_act_slot in ACTION_ALL_SLOTS,
                    'device':      state.last_device,
                    'room':        state.last_room,
                }]
            elif state.last_device and state.last_action:
                # Fallback: không có action trong slots
                actions = [{
                    'action':      state.last_action,
                    'action_slot': f'action_{state.last_action}-{state.last_action}',
                    'is_all':      False,
                    'device':      state.last_device,
                    'room':        state.last_room,
                }]
            else:
                return 'RESULT:error | control_device | result=error_no_action'

        results = []; slot_parts = []
        if signal: slot_parts.append(signal)

        for act_dict in actions:
            action   = act_dict.get('action', '')
            device   = act_dict.get('device', '')
            room     = act_dict.get('room')
            act_s    = act_dict.get('action_slot', '')
            is_all   = act_dict.get('is_all', False)
            lbl_vi   = ACTION_LABEL.get(action, action)

            if room is None and device and device not in NO_ROOM_DEVICES:
                # [FIX-3v9] action _all variant → expand tất cả rooms của device
                if is_all:
                    all_rooms = DEVICE_ROOMS.get(device, []) or []
                    for rm in all_rooms:
                        res = self._apply_action(state, device, rm, action)
                        results.append(res)
                    if act_s: slot_parts.append(act_s)
                    slot_parts.append(f'device-{device}')
                    slot_parts.append(f'action_label={lbl_vi}')
                    state.last_device = device
                    state.last_room   = None  # tất cả rooms, không lưu room cụ thể
                    state.last_action = action
                    continue

                # adj action → resolve từ last_room
                elif action in ('adj_up', 'adj_down') and state.last_room:
                    room = state.last_room

                # Thiếu room, cần hỏi
                else:
                    state.waiting_room = {'action': action, 'device': device, 'act_slot': act_s}
                    state.waiting_ttl  = MAX_WAIT_TURNS
                    rooms_str = ','.join(DEVICE_ROOMS.get(device, []) or [])
                    return f'__clarify__ | action={action} | device={device} | options={rooms_str}'

            result = self._apply_action(state, device, room, action)
            results.append(result)
            if act_s:   slot_parts.append(act_s)
            if device:  slot_parts.append(f'device-{device}')
            if room:    slot_parts.append(f'room-{room}')
            slot_parts.append(f'action_label={lbl_vi}')
            if value and action in ('adj_up', 'adj_down'):
                slot_parts.append(f'value={value}')
            # [FIX-7v9] Luôn update last_device/room/action sau execute
            state.last_device = device
            state.last_room   = room
            state.last_action = action

        return f'RESULT:{",".join(results)} | control_device | {" | ".join(slot_parts)}'

    # ------------------------------------------------------------------
    def _handle_confirm(self, slots, state: DialogState, raw_text: str = '') -> str:
        # [FIX-6v9] waiting_room non-context đã được xử lý ở waiting_room handler
        if not state.pending_action:
            return 'RESULT:no_pending | confirm_yes'

        actions = state.pending_action.get('actions', [])

        # Lấy room từ slots hoặc raw text
        room_from_slots = next(
            (ROOM_MAP[lbl[2:]] for _, lbl, _ in slots
             if lbl.startswith('B-') and lbl[2:] in ROOM_MAP), None)
        if not room_from_slots and raw_text:
            room_from_slots = _resolve_room_from_text(raw_text)

        # [FIX-2v9] CONTEXT_SUGGEST_NO_ASK đã bao gồm context_arrive và context_wake
        pending_intent  = state.pending_action.get('intent', '')
        needs_room_list = [(d, r, a) for d, r, a in actions if d in CONTEXT_SUGGEST_ASK_ROOM and r is None]
        if needs_room_list and not room_from_slots and pending_intent not in CONTEXT_SUGGEST_NO_ASK:
            first_dev, _, first_act = needs_room_list[0]
            act_slot = ('action_on-on' if first_act == 'on' else
                        'action_off-off' if first_act == 'off' else f'action_{first_act}-{first_act}')
            state.waiting_room = {
                'action': first_act, 'device': first_dev,
                'act_slot': act_slot, 'from_context': True
            }
            state.waiting_ttl = MAX_WAIT_TURNS
            opts = ','.join(DEVICE_ROOMS.get(first_dev, []))
            return f'__clarify__ | action={first_act} | device={first_dev} | options={opts}'

        # Điền room nếu user cung cấp
        if room_from_slots:
            actions = [(d, room_from_slots if (d in CONTEXT_SUGGEST_ASK_ROOM and r is None) else r, a)
                       for d, r, a in actions]

        results = []; detail_parts = []
        for dev, rm, act in actions:
            result = self._apply_action(state, dev, rm, act)
            results.append(result)
            # [FIX-4v9] Thêm detail device/room/action để NLG sinh đúng
            detail_parts.append(f'device-{dev}')
            if rm: detail_parts.append(f'room-{rm}')
            detail_parts.append(f'action_label={ACTION_LABEL.get(act, act)}')
            state.last_device = dev; state.last_room = rm; state.last_action = act

        state.pending_action = None; state.pending_ttl = 0
        detail_str = ' | '.join(detail_parts)
        return f'RESULT:{",".join(results)} | confirm_yes | {detail_str}'

    # ------------------------------------------------------------------
    def _handle_query_status(self, slots, state: DialogState) -> str:
        devices = []; rooms = []; slot_parts = []
        for _, lbl, _ in slots:
            raw = lbl[2:] if lbl.startswith(('B-', 'I-')) else lbl
            if raw in DEVICE_MAP and lbl.startswith('B-'):
                devices.append(DEVICE_MAP[raw]); slot_parts.append(f'device-{DEVICE_MAP[raw]}')
            elif raw in ROOM_MAP and lbl.startswith('B-'):
                rooms.append(ROOM_MAP[raw]); slot_parts.append(f'room-{ROOM_MAP[raw]}')

        if not devices and state.last_device:
            devices = [state.last_device]
            if state.last_room: rooms = [state.last_room]
        if not devices: return 'RESULT:unknown | query_status'

        if 'all' in devices:
            on_list  = [k for k, v in state.device_states.items() if v in ('on', 'unlocked')]
            off_list = [k for k, v in state.device_states.items() if v in ('off', 'locked')]
            on_str   = ','.join(on_list) or 'none'
            off_str  = ','.join(off_list) or 'none'
            return (f'RESULT:on:{on_str} | query_status | device-all'
                    f' | on_count={len(on_list)} | off_count={len(off_list)}'
                    f' | off:{off_str}')

        result_parts = []
        for i, device in enumerate(devices):
            room = rooms[i] if i < len(rooms) else (state.last_room if len(devices) == 1 else None)
            if device == 'door_lock':
                result_parts.append(f'door_lock:{state.device_states.get("door_lock", "unknown")}')
            else:
                key = _device_key(device, room)
                if key and key in state.device_states:
                    result_parts.append(f'{key}:{state.device_states[key]}')
                else:
                    result_parts.append(f'{device}_{room or "unknown"}:unknown')

        slot_str = ' | '.join(slot_parts)
        return f'RESULT:{",".join(result_parts)} | query_status | {slot_str}'

    # ------------------------------------------------------------------
    def _handle_query_sensor(self, slots) -> str:
        # [FIX] Chấp nhận cả B- lẫn I- khi không có B- nào (NLU đôi khi tag I- đầu câu)
        sensor_type = None
        for _, lbl, _ in slots:
            raw = lbl[2:] if lbl.startswith(('B-', 'I-')) else lbl
            if raw.startswith('sensor') and lbl.startswith('B-'):
                sensor_type = raw
                break
        # Fallback: nếu không có B-, lấy I- đầu tiên
        if sensor_type is None:
            for _, lbl, _ in slots:
                raw = lbl[2:] if lbl.startswith(('B-', 'I-')) else lbl
                if raw.startswith('sensor') and lbl.startswith('I-'):
                    sensor_type = raw
                    break

        # Lấy giá trị sensor: gọi API nếu có, fallback về self.sensor (mock)
        t = self.sensor['temp']
        h = self.sensor['hum']
        c = self.sensor['co2']

        if self.api:
            try:
                data = self.api.get_sensor_latest(SENSOR_TEMP_HUMI_ID)
                t_raw = data.get('temperature', data.get('temp'))
                h_raw = data.get('humidity',    data.get('hum'))
                if isinstance(t_raw, (int, float)): t = t_raw
                if isinstance(h_raw, (int, float)): h = h_raw
            except APIError as e:
                logger.warning(f"API sensor temp/humi lỗi, dùng mock: {e}")

            # CO2 — gọi riêng nếu server có endpoint, fallback mock nếu không
            try:
                co2_data = self.api.get_sensor_latest(SENSOR_LIGHT_ID)  # đổi thành sensor CO2 ID khi có
                c_raw = co2_data.get('co2', co2_data.get('ppm'))
                if isinstance(c_raw, (int, float)): c = c_raw
            except APIError:
                pass  # giữ mock CO2

        if not sensor_type or sensor_type == 'sensor-all':
            return (f'RESULT:temp:{t}C,hum:{h}%,co2:{c}ppm | query_sensor | sensor-all'
                    f' | level=temp:{_get_sensor_level(t, "sensor-temperature")},'
                    f'hum:{_get_sensor_level(h, "sensor-humidity")},'
                    f'co2:{_get_sensor_level(c, "sensor-co2")}')

        val_map = {
            'sensor-temperature': (f'{t}°C',   t, 'sensor-temperature'),
            'sensor-humidity':    (f'{h}%',     h, 'sensor-humidity'),
            'sensor-co2':         (f'{c}ppm',   c, 'sensor-co2'),
        }
        val_str, val_num, s_type = val_map.get(sensor_type, ('unknown', 0, sensor_type))
        level = _get_sensor_level(val_num, s_type)
        return f'RESULT:{val_str} | query_sensor | {sensor_type} | level={level}'

    # ------------------------------------------------------------------
    def _handle_query_weather(self) -> str:
        if self.api:
            try:
                data = self.api.get_weather()
                temp = data.get('temperature', '?')
                desc = data.get('description', '')
                city = data.get('city', 'Da Nang')
                return f'RESULT:{temp}°C | query_weather | city={city} | desc={desc}'
            except APIError:
                pass
        return 'RESULT:unavailable | query_weather'

    # ------------------------------------------------------------------
    def _handle_schedule(self, slots, state: DialogState) -> str:
        import re as _re
        actions, signal, _, time_abs, time_del, _ = _extract_slots(slots)

        # [FIX] Nếu không có device trong slots → lấy từ pending_action (context suggest)
        if not actions and state.pending_action:
            actions = [
                {'action': a, 'action_slot': f'action_{a}-{a}', 'is_all': False,
                 'device': d, 'room': r}
                for d, r, a in state.pending_action.get('actions', [])
            ]
            state.pending_action = None; state.pending_ttl = 0

        # Nếu vẫn không có device → lấy từ last context
        if not actions and state.last_device and state.last_action:
            actions = [{'action': state.last_action,
                        'action_slot': f'action_{state.last_action}-{state.last_action}',
                        'is_all': False,
                        'device': state.last_device, 'room': state.last_room}]

        # Parse delay_minutes từ string "1 phút nữa", "30 phút", ...
        delay_minutes = None
        if time_del:
            m = _re.search(r'(\d+)', time_del)
            if m: delay_minutes = int(m.group(1))

        if time_abs:
            time_part = f'time_absolute={time_abs}'
        elif time_del:
            time_part = f'time_delay={time_del}'
        else:
            now = datetime.now()
            time_part = f'time_absolute={now.strftime("%H:%M")}'

        parts = [f'RESULT:set | schedule_set | {time_part}']
        if signal: parts.append(signal)

        from config import DEVICE_ID_MAP as _DIM

        for act_dict in actions:
            action = act_dict.get('action', ''); device = act_dict.get('device', '')
            room   = act_dict.get('room');       act_s  = act_dict.get('action_slot', '')
            if room is None and device and device not in NO_ROOM_DEVICES:
                room = state.last_room
            if device == 'ventilation_fan': room = 'kitchen'
            if act_s:   parts.append(act_s)
            if device:  parts.append(f'device-{device}')
            if room:    parts.append(f'room-{room}')
            parts.append(f'action_label={ACTION_LABEL.get(action, action)}')
            state.last_device = device; state.last_room = room; state.last_action = action

            # [FIX] Gọi API thật nếu có client
            if self.api and device:
                try:
                    cmd = action.upper() if action in ('on', 'off') else action
                    did = _DIM.get((device, room))
                    if did:
                        if delay_minutes is not None:
                            self.api.set_timer({'device_id': did, 'command': cmd,
                                                'delay_minutes': delay_minutes})
                        elif time_abs:
                            execute_at = f"{datetime.now().strftime('%Y-%m-%d')}T{time_abs}:00"
                            self.api.set_schedule({'device_id': did, 'command': cmd,
                                                   'time': execute_at})
                except (APIError, Exception) as e:
                    logger.warning(f"API schedule loi: {e}")

        result = ' | '.join(parts)
        state.last_schedule = result
        return result

    # ------------------------------------------------------------------
    def _handle_alarm(self, slots, state: DialogState, mode: str = 'set') -> str:
        time_abs_words = []; time_del_words = []
        for word, lbl, _ in slots:
            raw = lbl[2:] if lbl.startswith(('B-', 'I-')) else lbl
            if raw == 'time_absolute': time_abs_words.append(word)
            elif raw == 'time_delay':  time_del_words.append(word)

        if time_abs_words:
            time_str  = ' '.join(time_abs_words)
            time_part = f'time_absolute={time_str}'
        elif time_del_words:
            time_str  = ' '.join(time_del_words)
            time_part = f'time_delay={time_str}'
        else:
            time_str  = datetime.now().strftime('%H:%M')
            time_part = f'time_absolute={time_str}'

        if mode == 'set':
            state.last_alarm = time_str
        return f'RESULT:{mode} | alarm_{mode} | {time_part}'

    # ------------------------------------------------------------------
    def _handle_cancel(self, cancel_type: str, state: DialogState) -> str:
        has_alarm    = bool(state.last_alarm)
        has_schedule = bool(state.last_schedule)
        if cancel_type == 'alarm'    and not has_alarm    and has_schedule: cancel_type = 'schedule'
        elif cancel_type == 'schedule' and not has_schedule and has_alarm:  cancel_type = 'alarm'

        if cancel_type == 'alarm':
            ref = state.last_alarm or 'unknown'; state.last_alarm = None
            return f'RESULT:cancelled | alarm_cancel | time_absolute={ref}'
        else:
            state.last_schedule = None
            return 'RESULT:cancelled | schedule_cancel'

    # ------------------------------------------------------------------
    def _handle_context(self, intent: str, slots, state: DialogState) -> str:
        signal = None
        for _, lbl, _ in slots:
            raw = lbl[2:] if lbl.startswith(('B-', 'I-')) else lbl
            if raw.startswith('signal') and lbl.startswith('B-'):
                signal = raw; break
        if not signal: signal = INTENT_SIGNAL_MAP.get(intent)

        suggestions = CONTEXT_SUGGEST.get(intent, [])
        if not suggestions:
            return f'{intent}{" | " + signal if signal else ""} | result=noted'

        state.pending_action = {
            'actions': [(d, r, a) for d, r, a in suggestions],
            'intent':  intent
        }
        state.pending_ttl = MAX_PENDING_TURNS

        suggest_str = ','.join(
            f'{d}_{r}:{a}' if r else f'{d}:{a}' for d, r, a in suggestions
        )
        sig_part = f' | {signal}' if signal else ''
        return f'{intent}{sig_part} | suggest={suggest_str}'