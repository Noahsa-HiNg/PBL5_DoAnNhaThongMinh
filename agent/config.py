"""
config.py — Cấu hình tập trung cho Smart Home Pipeline
"""

import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ─────────────────────────────────────────────
#  API SERVER
# ─────────────────────────────────────────────
API_BASE_URL = "http://172.16.24.13:8000/"
API_TIMEOUT  = 5   # seconds

# ─────────────────────────────────────────────
#  NLU PATHS
# ─────────────────────────────────────────────
NLU_MODEL_PATH = os.path.join(BASE_DIR, "model", "micro_bert_best.pt")
NLU_TOKENIZER  = os.path.join(BASE_DIR, "tokenizer", "vi_smarthome_bpe.model")

# ─────────────────────────────────────────────
#  NLG PATHS
# ─────────────────────────────────────────────
NLG_MODEL_DIR = os.path.join(BASE_DIR, "model", "vit5-nlg-smarthome")

# ─────────────────────────────────────────────
#  DEVICE MAPPING  (device_type, room) → device_id
#  Khớp với api_specification.md
# ─────────────────────────────────────────────
DEVICE_ID_MAP = {
    # Đèn
    ('light', 'living_room'): 1,
    ('light', 'bedroom'):     2,
    ('light', 'kitchen'):     3,
    ('light', 'yard'):        4,
    # Quạt
    ('fan', 'living_room'):   5,
    ('fan', 'bedroom'):       6,
    ('fan', 'kitchen'):       7,
    # Quạt thông gió — room cố định là kitchen
    ('ventilation_fan', 'kitchen'): 8,
    # Cảm biến
    ('sensor_temp_humi', None): 9,
    ('sensor_light', None):     10,
    # Cửa khóa — không có room
    ('door_lock', None):        11,
    # Buzzer / Loa
    ('buzzer', 'bedroom'):      12,
}

# Tên thiết bị hiển thị (để log)
DEVICE_NAMES = {
    1:  "Đèn Phòng Khách",
    2:  "Đèn Phòng Ngủ",
    3:  "Đèn Bếp",
    4:  "Đèn Sân Vườn",
    5:  "Quạt Phòng Khách",
    6:  "Quạt Phòng Ngủ",
    7:  "Quạt Bếp",
    8:  "Quạt Thông Gió",
    9:  "Cảm biến Nhiệt ẩm",
    10: "Cảm biến Ánh sáng",
    11: "Cửa Chính",
    12: "Loa (Buzzer)",
}

# Sensor device_id mặc định
SENSOR_TEMP_HUMI_ID = 9
SENSOR_LIGHT_ID     = 10
DOOR_LOCK_ID        = 11

# ─────────────────────────────────────────────
#  NLG GENERATION PARAMS
# ─────────────────────────────────────────────
NLG_MAX_INPUT   = 128
NLG_MAX_NEW_TOK = 64
NLG_NUM_BEAMS   = 4

# ─────────────────────────────────────────────
#  NLU INFERENCE PARAMS
# ─────────────────────────────────────────────
NLU_THRESHOLD = 0.5
