"""
dialog_manager.py — Dialog Manager v9 tích hợp API thật
Ported từ SmartHome_DialogManager_v9.ipynb (Cell 7 + Cell 9)
Thay mock bằng SmartHomeAPIClient thật.
"""

import logging
from datetime import datetime
from typing import Optional, Dict, List, Tuple

from dialog_state import DialogState, DEFAULT_DEVICE_STATES
from api_client import SmartHomeAPIClient, APIError
from config import SENSOR_TEMP_HUMI_ID, SENSOR_LIGHT_ID, DOOR_LOCK_ID

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
#  CONSTANTS
# ─────────────────────────────────────────────
MAX_PENDING_TURNS = 3
MAX_WAIT_TURNS    = 2

# Intent không tick TTL (FIX-5 v9)
NON_TICK_INTENTS = {
    'query_time', 'query_weather', 'query_sensor',
    'query_status', 'chitchat', 'unsupported',
}

# Map từ ngôn ngữ tự nhiên → room slug
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

# Map slot label → internal key
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

# FIX-3 v9: action slot có suffix _all → expand tất cả rooms
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

# Các phòng mà mỗi loại thiết bị có thể ở
DEVICE_ROOMS = {
    'light':           ['living_room', 'bedroom', 'kitchen', 'yard'],
    'fan':             ['living_room', 'bedroom', 'kitchen'],
    'ventilation_fan': ['kitchen'],
    'door_lock':       None,
    'all':             None,
}

# Thiết bị không cần room
NO_ROOM_DEVICES = {'door_lock', 'all', 'ventilation_fan'}

# Device cần hỏi phòng khi confirm sau context suggest
CONTEXT_SUGGEST_ASK_ROOM = {'fan', 'light'}

# FIX-2 v9: intent có room cố định, không cần hỏi thêm
CONTEXT_SUGGEST_NO_ASK = {
    'context_cold', 'context_sleep', 'context_leave', 'context_stuffy',
    'context_arrive', 'context_wake',
}

# Gợi ý hành động theo context
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


# ─────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────

def _time_context(hour: int) -> str:
    if 5 <= hour < 12:  return 'morning'
    if 12 <= hour < 17: return 'afternoon'
    if 17 <= hour < 21: return 'evening'
    return 'night'


def _device_key(device: str, room: Optional[str]) -> Optional[str]:
    """Tạo key để tra trạng thái local."""
    if device == 'door_lock':        return 'door_lock'
    if device == 'ventilation_fan':  return 'ventilation_fan_kitchen'
    if device == 'all' or room == 'all': return 'all'
    if room: return f'{device}_{room}'
    return None


def _get_sensor_level(value: float, sensor_type: str) -> str:
    if sensor_type == 'sensor-temperature':
        return 'high' if value > 35 else ('low' if value < 18 else 'normal')
    elif sensor_type == 'sensor-humidity':
        return 'high' if value > 80 else ('low' if value < 40 else 'normal')
    elif sensor_type == 'sensor-co2':
        return 'high' if value > 1000 else ('medium' if value > 700 else 'normal')
    return 'normal'


def _resolve_room_from_text(raw_text: str) -> Optional[str]:
    """Tìm room slug từ text tự do."""
    text_lower = raw_text.lower().strip()
    for vi, key in sorted(ROOM_VI_MAP.items(), key=lambda x: -len(x[0])):
        if vi in text_lower:
            return key
    return None


def _extract_action_only(slots: List) -> Optional[Tuple[str, str]]:
    """
    FIX-1 v9: Lấy action đầu tiên từ slots dù không có device.
    Dùng cho "tăng lên", "tắt đi", v.v.
    Trả về (action_value, action_slot_raw) hoặc None.
    """
    for _, lbl, _ in slots:
        raw = lbl[2:] if lbl.startswith(('B-', 'I-')) else lbl
        if lbl.startswith('B-') and raw in ACTION_MAP:
            return (ACTION_MAP[raw], raw)
    return None


def _extract_slots(slots: List) -> Tuple:
    """
    Parse danh sách slot từ NLU output.
    Xử lý: Orphan I-, multi-action, multi-room, multi-device.
    Trả về: (actions, signal, sensor, time_abs, time_del, value)
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
        if not ca.get('action'):
            return []
        devices = ca.get('devices', [])
        if not devices and ca.get('device'):
            devices = [ca['device']]
        if not devices:
            return []
        rooms = ca.get('rooms', [])
        if not rooms:
            rooms = [None]
        return [
            {
                'action':      ca['action'],
                'action_slot': ca.get('action_slot', ''),
                'is_all':      ca.get('is_all', False),
                'device':      dev,
                'room':        rm,
            }
            for dev in devices for rm in rooms
        ]

    for word, lbl, conf in slots:
        raw      = lbl[2:] if lbl.startswith(('B-', 'I-')) else lbl
        is_begin = lbl.startswith('B-')
        is_inner = lbl.startswith('I-')

        # Orphan I- fix
        if is_inner and raw != last_entity_type:
            if raw in ACTION_MAP:
                last_entity_type = raw
                continue
            else:
                is_begin = True
                is_inner = False

        if raw in ACTION_MAP:
            last_entity_type = raw
            if is_begin:
                actions.extend(_flush_current(current_action))
                # FIX-3 v9: đánh dấu is_all
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
            if is_begin:
                sensor = raw
        elif raw.startswith('signal'):
            last_entity_type = raw
            if is_begin:
                signal = raw
        elif raw == 'time_absolute':
            last_entity_type = raw
            time_abs_words.append(word)
        elif raw == 'time_delay':
            last_entity_type = raw
            time_del_words.append(word)
        elif raw == 'value':
            last_entity_type = raw
            value_words.append(word)
        else:
            last_entity_type = None

    actions.extend(_flush_current(current_action))

    return (
        actions,
        signal,
        sensor,
        ' '.join(time_abs_words) or None,
        ' '.join(time_del_words) or None,
        ' '.join(value_words)    or None,
    )


# ─────────────────────────────────────────────
#  DIALOG MANAGER
# ─────────────────────────────────────────────

class SmartHomeDialogManager:
    """
    Dialog Manager v9 — tích hợp SmartHomeAPIClient thật.
    Mỗi lần điều khiển thiết bị, gọi API server thay vì mock local.
    Nếu API lỗi, vẫn trả DM output có trạng thái 'error' để NLG thông báo lỗi.
    """

    def __init__(self, api_client: Optional[SmartHomeAPIClient] = None):
        self.state  = DialogState()
        self.api    = api_client or SmartHomeAPIClient()

    def reset(self):
        """Reset dialog state."""
        self.state.reset()

    def process(self, nlu_result: Dict, raw_text: str = '') -> str:
        """
        Entry point: nhận NLU result dict, trả về DM output string.
        """
        intent = nlu_result['intent']
        slots  = nlu_result['slots']
        state  = self.state

        state.last_intent = intent
        state.history.append(intent)

        # FIX-5 v9: chỉ tick TTL khi intent là action/confirm
        if intent not in NON_TICK_INTENTS:
            if state.pending_action:
                state.pending_ttl -= 1
                if state.pending_ttl <= 0:
                    state.pending_action = None
                    state.pending_ttl    = 0
            if state.waiting_room:
                state.waiting_ttl -= 1
                if state.waiting_ttl <= 0:
                    state.waiting_room = None
                    state.waiting_ttl  = 0

        # ── FIX-6 v9: waiting_room handler TRƯỚC khi dispatch ──────────
        if state.waiting_room:
            room_from_slots = next(
                (ROOM_MAP[lbl[2:]] for _, lbl, _ in slots
                 if lbl.startswith('B-') and lbl[2:] in ROOM_MAP),
                None
            )
            if not room_from_slots and raw_text:
                room_from_slots = _resolve_room_from_text(raw_text)

            if room_from_slots:
                pending_wr = state.waiting_room
                state.waiting_room = None
                state.waiting_ttl  = 0

                if pending_wr.get('from_context') and state.pending_action:
                    # Resolve context suggest với room vừa cung cấp
                    pa_actions = state.pending_action.get('actions', [])
                    pa_actions = [
                        (d, room_from_slots if d in CONTEXT_SUGGEST_ASK_ROOM else r, a)
                        for d, r, a in pa_actions
                    ]
                    results = []
                    detail_parts = []
                    for dev, rm, act in pa_actions:
                        api_res = self._call_api(dev, rm, act)
                        results.append(api_res)
                        detail_parts += [
                            f'device-{dev}',
                            f'room-{rm}' if rm else '',
                            f'action_label={ACTION_LABEL.get(act, act)}',
                        ]
                        state.last_device = dev
                        state.last_room   = rm
                        state.last_action = act
                        state.update_device_state(dev, rm, act if act in ('on', 'off') else state.state if hasattr(state, 'state') else act)
                    state.pending_action = None
                    state.pending_ttl    = 0
                    detail_str = ' | '.join(p for p in detail_parts if p)
                    return f'RESULT:{",".join(results)} | confirm_yes | {detail_str}'

                # Resolve đơn lẻ (waiting_room từ clarify)
                api_res = self._call_api(
                    pending_wr['device'], room_from_slots, pending_wr['action']
                )
                state.last_device = pending_wr['device']
                state.last_room   = room_from_slots
                state.last_action = pending_wr['action']
                state.update_device_state(pending_wr['device'], room_from_slots, pending_wr['action'])
                lbl_vi = ACTION_LABEL.get(pending_wr['action'], pending_wr['action'])
                return (
                    f"RESULT:{api_res} | control_device"
                    f" | {pending_wr['act_slot']}"
                    f" | device-{pending_wr['device']}"
                    f" | room-{room_from_slots}"
                    f" | action_label={lbl_vi}"
                )
            # Không có room → pass qua, intent xử lý bình thường
        # ────────────────────────────────────────────────────────────────

        # Dispatch theo intent
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
        elif intent in CONTEXT_SUGGEST:
            return self._handle_context(intent, slots, state)
        elif intent == 'confirm_yes':
            return self._handle_confirm(slots, state, raw_text=raw_text)
        elif intent == 'confirm_no':
            state.pending_action = None
            state.pending_ttl    = 0
            state.waiting_room   = None
            state.waiting_ttl    = 0
            return 'RESULT:cancelled | confirm_no'
        elif intent == 'chitchat':
            return 'RESULT:ok | chitchat | question=general'
        else:
            return 'RESULT:unsupported | unsupported'

    # ── API wrapper ────────────────────────────────────────────────────

    def _call_api(self, device: str, room: Optional[str], action: str) -> str:
        """
        Gọi API thích hợp dựa trên device + action.
        Trả về chuỗi kết quả cho DM output (vd: 'light_bedroom:on').
        Không raise exception — lỗi trả về 'error'.
        """
        try:
            if device == 'light':
                device_id = self.api.get_device_id('light', room)
                state_val = 'on' if action == 'on' else 'off'
                self.api.control_light(device_id, state_val)
                key = f'light_{room}' if room else 'light'
                return f'{key}:{action}'

            elif device == 'fan':
                device_id = self.api.get_device_id('fan', room)
                if action in ('on', 'off'):
                    self.api.control_fan(device_id, action)
                    key = f'fan_{room}' if room else 'fan'
                    return f'{key}:{action}'
                elif action == 'adj_up':
                    self.api.adjust_fan(device_id, 'up')
                    key = f'fan_{room}' if room else 'fan'
                    return f'{key}:adjusted'
                elif action == 'adj_down':
                    self.api.adjust_fan(device_id, 'down')
                    key = f'fan_{room}' if room else 'fan'
                    return f'{key}:adjusted'

            elif device == 'ventilation_fan':
                device_id = self.api.get_device_id('ventilation_fan', 'kitchen')
                if action in ('on', 'off'):
                    self.api.control_fan(device_id, action)
                return f'ventilation_fan_kitchen:{action}'

            elif device == 'door_lock':
                device_id = DOOR_LOCK_ID
                if action in ('lock', 'unlock'):
                    self.api.control_door(device_id, action)
                    result_state = 'locked' if action == 'lock' else 'unlocked'
                    return f'door_lock:{result_state}'

            elif device == 'buzzer':
                device_id = self.api.get_device_id('buzzer', room)
                self.api.control_buzzer(device_id, action)
                return f'buzzer_{room}:{action}' if room else f'buzzer:{action}'

            elif device == 'all':
                if action in ('on', 'off'):
                    self.api.bulk_all(action)
                return f'all:{action}'

            return 'unknown'

        except APIError as e:
            logger.error(f"API error [{e.error_code}]: {e}")
            return f'error:{e.error_code}'
        except Exception as e:
            logger.error(f"Unexpected error calling API: {e}")
            return 'error:UNKNOWN'

    # ── Handlers ──────────────────────────────────────────────────────

    def _handle_control(self, slots: List, state: DialogState) -> str:
        actions_raw, signal, _, time_abs, time_del, value = _extract_slots(slots)
        actions = [a for a in actions_raw if a.get('device')]

        # FIX-1 v9: actions rỗng → lấy action từ NLU
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
                actions = [{
                    'action':      state.last_action,
                    'action_slot': f'action_{state.last_action}-{state.last_action}',
                    'is_all':      False,
                    'device':      state.last_device,
                    'room':        state.last_room,
                }]
            else:
                return 'RESULT:error | control_device | result=error_no_action'

        results     = []
        slot_parts  = []
        if signal:
            slot_parts.append(signal)

        for act_dict in actions:
            action  = act_dict.get('action', '')
            device  = act_dict.get('device', '')
            room    = act_dict.get('room')
            act_s   = act_dict.get('action_slot', '')
            is_all  = act_dict.get('is_all', False)
            lbl_vi  = ACTION_LABEL.get(action, action)

            if room is None and device and device not in NO_ROOM_DEVICES:
                # FIX-3 v9: action_all → expand tất cả rooms
                if is_all:
                    all_rooms = DEVICE_ROOMS.get(device, []) or []
                    for rm in all_rooms:
                        res = self._call_api(device, rm, action)
                        results.append(res)
                        state.update_device_state(device, rm, action)
                    if act_s:
                        slot_parts.append(act_s)
                    slot_parts.append(f'device-{device}')
                    slot_parts.append(f'action_label={lbl_vi}')
                    state.last_device = device
                    state.last_room   = None
                    state.last_action = action
                    continue

                elif action in ('adj_up', 'adj_down') and state.last_room:
                    room = state.last_room

                else:
                    # Cần hỏi phòng
                    state.waiting_room = {
                        'action':   action,
                        'device':   device,
                        'act_slot': act_s,
                    }
                    state.waiting_ttl = MAX_WAIT_TURNS
                    rooms_str = ','.join(DEVICE_ROOMS.get(device, []) or [])
                    return f'__clarify__ | action={action} | device={device} | options={rooms_str}'

            api_res = self._call_api(device, room, action)
            results.append(api_res)
            state.update_device_state(device, room, action)

            if act_s:
                slot_parts.append(act_s)
            if device:
                slot_parts.append(f'device-{device}')
            if room:
                slot_parts.append(f'room-{room}')
            slot_parts.append(f'action_label={lbl_vi}')
            if value and action in ('adj_up', 'adj_down'):
                slot_parts.append(f'value={value}')

            # FIX-7 v9: luôn update last context
            state.last_device = device
            state.last_room   = room
            state.last_action = action

        return f'RESULT:{",".join(results)} | control_device | {" | ".join(slot_parts)}'

    def _handle_confirm(self, slots: List, state: DialogState, raw_text: str = '') -> str:
        if not state.pending_action:
            return 'RESULT:no_pending | confirm_yes'

        actions = state.pending_action.get('actions', [])

        room_from_slots = next(
            (ROOM_MAP[lbl[2:]] for _, lbl, _ in slots
             if lbl.startswith('B-') and lbl[2:] in ROOM_MAP),
            None
        )
        if not room_from_slots and raw_text:
            room_from_slots = _resolve_room_from_text(raw_text)

        # FIX-2 v9
        pending_intent  = state.pending_action.get('intent', '')
        needs_room_list = [
            (d, r, a) for d, r, a in actions
            if d in CONTEXT_SUGGEST_ASK_ROOM and r is None
        ]
        if needs_room_list and not room_from_slots and pending_intent not in CONTEXT_SUGGEST_NO_ASK:
            first_dev, _, first_act = needs_room_list[0]
            act_slot = (
                'action_on-on'  if first_act == 'on'  else
                'action_off-off' if first_act == 'off' else
                f'action_{first_act}-{first_act}'
            )
            state.waiting_room = {
                'action': first_act, 'device': first_dev,
                'act_slot': act_slot, 'from_context': True,
            }
            state.waiting_ttl = MAX_WAIT_TURNS
            opts = ','.join(DEVICE_ROOMS.get(first_dev, []))
            return f'__clarify__ | action={first_act} | device={first_dev} | options={opts}'

        if room_from_slots:
            actions = [
                (d, room_from_slots if (d in CONTEXT_SUGGEST_ASK_ROOM and r is None) else r, a)
                for d, r, a in actions
            ]

        results = []
        detail_parts = []
        for dev, rm, act in actions:
            api_res = self._call_api(dev, rm, act)
            results.append(api_res)
            state.update_device_state(dev, rm, act)
            # FIX-4 v9
            detail_parts.append(f'device-{dev}')
            if rm:
                detail_parts.append(f'room-{rm}')
            detail_parts.append(f'action_label={ACTION_LABEL.get(act, act)}')
            state.last_device = dev
            state.last_room   = rm
            state.last_action = act

        state.pending_action = None
        state.pending_ttl    = 0
        detail_str = ' | '.join(detail_parts)
        return f'RESULT:{",".join(results)} | confirm_yes | {detail_str}'

    def _handle_query_status(self, slots: List, state: DialogState) -> str:
        devices    = []
        rooms      = []
        slot_parts = []

        for _, lbl, _ in slots:
            raw = lbl[2:] if lbl.startswith(('B-', 'I-')) else lbl
            if raw in DEVICE_MAP and lbl.startswith('B-'):
                devices.append(DEVICE_MAP[raw])
                slot_parts.append(f'device-{DEVICE_MAP[raw]}')
            elif raw in ROOM_MAP and lbl.startswith('B-'):
                rooms.append(ROOM_MAP[raw])
                slot_parts.append(f'room-{ROOM_MAP[raw]}')

        if not devices and state.last_device:
            devices = [state.last_device]
            if state.last_room:
                rooms = [state.last_room]
        if not devices:
            return 'RESULT:unknown | query_status'

        if 'all' in devices:
            on_list  = [k for k, v in state.device_states.items() if v in ('on', 'unlocked')]
            off_list = [k for k, v in state.device_states.items() if v in ('off', 'locked')]
            on_str   = ','.join(on_list) or 'none'
            off_str  = ','.join(off_list) or 'none'
            return (
                f'RESULT:on:{on_str} | query_status | device-all'
                f' | on_count={len(on_list)} | off_count={len(off_list)}'
                f' | off:{off_str}'
            )

        result_parts = []
        for i, device in enumerate(devices):
            room = rooms[i] if i < len(rooms) else (state.last_room if len(devices) == 1 else None)
            result_parts.append(
                f'{device}_{room}:{state.get_device_state(device, room)}'
                if room else
                f'{device}:{state.get_device_state(device, room)}'
            )

        slot_str = ' | '.join(slot_parts)
        return f'RESULT:{",".join(result_parts)} | query_status | {slot_str}'

    def _handle_query_sensor(self, slots: List) -> str:
        sensor_type = None
        for _, lbl, _ in slots:
            raw = lbl[2:] if lbl.startswith(('B-', 'I-')) else lbl
            if raw.startswith('sensor') and lbl.startswith('B-'):
                sensor_type = raw
                break

        try:
            # Gọi API lấy dữ liệu cảm biến thật
            data = self.api.get_sensor_latest(SENSOR_TEMP_HUMI_ID)
            t = data.get('temperature', data.get('temp', 0))
            h = data.get('humidity',    data.get('hum', 0))

            # Thử lấy CO2 nếu có sensor riêng
            try:
                data_light = self.api.get_sensor_latest(SENSOR_LIGHT_ID)
                c = data_light.get('co2', 0)
            except APIError:
                c = 0

        except APIError as e:
            logger.warning(f"Không lấy được sensor data: {e}")
            return 'RESULT:unavailable | query_sensor | result=sensor_error'

        if not sensor_type or sensor_type == 'sensor-all':
            return (
                f'RESULT:temp:{t}C,hum:{h}%,co2:{c}ppm | query_sensor | sensor-all'
                f' | level=temp:{_get_sensor_level(t, "sensor-temperature")},'
                f'hum:{_get_sensor_level(h, "sensor-humidity")},'
                f'co2:{_get_sensor_level(c, "sensor-co2")}'
            )

        val_map = {
            'sensor-temperature': (f'{t}°C',   t, 'sensor-temperature'),
            'sensor-humidity':    (f'{h}%',     h, 'sensor-humidity'),
            'sensor-co2':         (f'{c}ppm',   c, 'sensor-co2'),
        }
        val_str, val_num, s_type = val_map.get(sensor_type, ('unknown', 0, sensor_type))
        level = _get_sensor_level(val_num, s_type)
        return f'RESULT:{val_str} | query_sensor | {sensor_type} | level={level}'

    def _handle_query_time(self) -> str:
        try:
            data = self.api.get_time()
            time_str = data.get('time', '')
            ctx      = data.get('context', '')
            return f'RESULT:{time_str} | query_time | context={ctx}'
        except APIError:
            # Fallback: dùng giờ máy local
            now  = datetime.now()
            hhmm = now.strftime('%H:%M')
            ctx  = _time_context(now.hour)
            return f'RESULT:{hhmm} | query_time | context={ctx}'

    def _handle_query_weather(self) -> str:
        try:
            data = self.api.get_weather()
            temp = data.get('temperature', '?')
            desc = data.get('description', '')
            city = data.get('city', 'Da Nang')
            return f'RESULT:{temp}°C | query_weather | city={city} | desc={desc}'
        except APIError as e:
            logger.warning(f"Không lấy được weather: {e}")
            return 'RESULT:unavailable | query_weather'

    def _handle_schedule(self, slots: List, state: DialogState) -> str:
        actions, signal, _, time_abs, time_del, _ = _extract_slots(slots)

        if time_abs:
            time_part = f'time_absolute={time_abs}'
        elif time_del:
            time_part = f'time_delay={time_del}'
        else:
            now = datetime.now()
            time_part = f'time_absolute={now.strftime("%H:%M")}'

        parts = [f'RESULT:set | schedule_set | {time_part}']
        if signal:
            parts.append(signal)

        for act_dict in actions:
            action = act_dict.get('action', '')
            device = act_dict.get('device', '')
            room   = act_dict.get('room')
            act_s  = act_dict.get('action_slot', '')
            if room is None and device and device not in NO_ROOM_DEVICES:
                room = state.last_room
            if act_s:
                parts.append(act_s)
            if device:
                parts.append(f'device-{device}')
            if room:
                parts.append(f'room-{room}')
            parts.append(f'action_label={ACTION_LABEL.get(action, action)}')
            state.last_device = device
            state.last_room   = room
            state.last_action = action

        result = ' | '.join(parts)
        state.last_schedule = result
        return result

    def _handle_alarm(self, slots: List, state: DialogState, mode: str = 'set') -> str:
        time_abs_words = []
        time_del_words = []
        for word, lbl, _ in slots:
            raw = lbl[2:] if lbl.startswith(('B-', 'I-')) else lbl
            if raw == 'time_absolute':
                time_abs_words.append(word)
            elif raw == 'time_delay':
                time_del_words.append(word)

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

    def _handle_cancel(self, cancel_type: str, state: DialogState) -> str:
        has_alarm    = bool(state.last_alarm)
        has_schedule = bool(state.last_schedule)
        if cancel_type == 'alarm'    and not has_alarm    and has_schedule:
            cancel_type = 'schedule'
        elif cancel_type == 'schedule' and not has_schedule and has_alarm:
            cancel_type = 'alarm'

        if cancel_type == 'alarm':
            ref = state.last_alarm or 'unknown'
            state.last_alarm = None
            return f'RESULT:cancelled | alarm_cancel | time_absolute={ref}'
        else:
            state.last_schedule = None
            return 'RESULT:cancelled | schedule_cancel'

    def _handle_context(self, intent: str, slots: List, state: DialogState) -> str:
        signal = None
        for _, lbl, _ in slots:
            raw = lbl[2:] if lbl.startswith(('B-', 'I-')) else lbl
            if raw.startswith('signal') and lbl.startswith('B-'):
                signal = raw
                break
        if not signal:
            signal = INTENT_SIGNAL_MAP.get(intent)

        suggestions = CONTEXT_SUGGEST.get(intent, [])
        if not suggestions:
            return f'{intent}{" | " + signal if signal else ""} | result=noted'

        state.pending_action = {
            'actions': [(d, r, a) for d, r, a in suggestions],
            'intent':  intent,
        }
        state.pending_ttl = MAX_PENDING_TURNS

        suggest_str = ','.join(
            f'{d}_{r}:{a}' if r else f'{d}:{a}'
            for d, r, a in suggestions
        )
        sig_part = f' | {signal}' if signal else ''
        return f'{intent}{sig_part} | suggest={suggest_str}'
