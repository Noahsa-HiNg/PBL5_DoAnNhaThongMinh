"""
stt_normalizer.py — Chuẩn hóa output STT (PhoWhisper) trước khi đưa vào NLU

Vấn đề: Whisper thường output số Arabic, giờ dạng số, ký hiệu...
Mục tiêu: Chuyển về dạng văn bản tự nhiên tiếng Việt, khớp với dataset NLU.

Pipeline: STT output → stt_normalizer → NLU input

Ví dụ:
  "bật đèn lúc 6:30 tối"  →  "bật đèn lúc sáu giờ ba mươi tối"
  "sau 15 phút tắt quạt"  →  "sau mười lăm phút tắt quạt"
  "đặt báo thức 7h sáng"  →  "đặt báo thức bảy giờ sáng"
  "tăng lên 50%"          →  "tăng lên năm mươi phần trăm"
  "mức 3"                 →  "mức ba"
"""

import re


# ══════════════════════════════════════════════════════════════════
#  BẢNG SỐ → CHỮ
# ══════════════════════════════════════════════════════════════════

_UNITS = {
    0: 'không', 1: 'một', 2: 'hai', 3: 'ba', 4: 'bốn',
    5: 'năm', 6: 'sáu', 7: 'bảy', 8: 'tám', 9: 'chín',
    10: 'mười', 11: 'mười một', 12: 'mười hai', 13: 'mười ba',
    14: 'mười bốn', 15: 'mười lăm', 16: 'mười sáu', 17: 'mười bảy',
    18: 'mười tám', 19: 'mười chín',
    20: 'hai mươi', 21: 'hai mươi mốt', 22: 'hai mươi hai',
    23: 'hai mươi ba', 24: 'hai mươi bốn', 25: 'hai mươi lăm',
    26: 'hai mươi sáu', 27: 'hai mươi bảy', 28: 'hai mươi tám',
    29: 'hai mươi chín', 30: 'ba mươi', 31: 'ba mươi mốt',
    32: 'ba mươi hai', 33: 'ba mươi ba', 34: 'ba mươi bốn',
    35: 'ba mươi lăm', 36: 'ba mươi sáu', 37: 'ba mươi bảy',
    38: 'ba mươi tám', 39: 'ba mươi chín', 40: 'bốn mươi',
    41: 'bốn mươi mốt', 42: 'bốn mươi hai', 43: 'bốn mươi ba',
    44: 'bốn mươi bốn', 45: 'bốn mươi lăm', 46: 'bốn mươi sáu',
    47: 'bốn mươi bảy', 48: 'bốn mươi tám', 49: 'bốn mươi chín',
    50: 'năm mươi', 51: 'năm mươi mốt', 52: 'năm mươi hai',
    53: 'năm mươi ba', 54: 'năm mươi bốn', 55: 'năm mươi lăm',
    56: 'năm mươi sáu', 57: 'năm mươi bảy', 58: 'năm mươi tám',
    59: 'năm mươi chín', 60: 'sáu mươi', 100: 'một trăm',
}


def _num_to_word(n: int) -> str:
    """Chuyển số nguyên (0–100) sang chữ tiếng Việt."""
    if n in _UNITS:
        return _UNITS[n]
    if n < 100:
        tens = (n // 10) * 10
        unit = n % 10
        tens_word = _UNITS[tens]
        if unit == 1:
            unit_word = 'mốt'
        elif unit == 5:
            unit_word = 'lăm'
        else:
            unit_word = _UNITS[unit]
        return f"{tens_word} {unit_word}"
    return str(n)  # fallback


# ══════════════════════════════════════════════════════════════════
#  CÁC HÀM CONVERT THEO TỪNG PATTERN
# ══════════════════════════════════════════════════════════════════

def _convert_time_colon(match: re.Match) -> str:
    """
    HH:MM → "H giờ MM phút"  (bỏ "phút" nếu MM=00)
    Ví dụ: 6:30 → "sáu giờ ba mươi phút", 8:00 → "tám giờ"
    """
    h = int(match.group(1))
    m = int(match.group(2))
    h_word = _num_to_word(h)
    if m == 0:
        return f"{h_word} giờ"
    else:
        m_word = _num_to_word(m)
        return f"{h_word} giờ {m_word} phút"


def _convert_time_h(match: re.Match) -> str:
    """
    Xh / Xh → "X giờ"
    Ví dụ: 7h → "bảy giờ", 10H → "mười giờ"
    """
    h = int(match.group(1))
    return f"{_num_to_word(h)} giờ"


def _convert_minutes(match: re.Match) -> str:
    """
    X phút → "X_word phút"
    Ví dụ: 15 phút → "mười lăm phút", 30 phút → "ba mươi phút"
    """
    n = int(match.group(1))
    return f"{_num_to_word(n)} phút"


def _convert_percent(match: re.Match) -> str:
    """
    X% → "X_word phần trăm"
    Ví dụ: 50% → "năm mươi phần trăm"
    """
    n = int(match.group(1))
    return f"{_num_to_word(n)} phần trăm"


def _convert_level(match: re.Match) -> str:
    """
    mức X / level X → "mức X_word"
    Ví dụ: mức 3 → "mức ba"
    """
    prefix = match.group(1).lower()  # "mức" hoặc "level"
    n = int(match.group(2))
    if prefix == 'level':
        prefix = 'mức'
    return f"{prefix} {_num_to_word(n)}"


def _convert_standalone_hour(match: re.Match) -> str:
    """
    Số đứng một mình trước/sau từ chỉ thời điểm
    Ví dụ: "lúc 6 sáng" → "lúc sáu sáng"
            "6 giờ sáng" → "sáu giờ sáng"
    """
    before = match.group(1) or ''  # từ trước có thể None nếu optional
    n      = int(match.group(2))
    after  = match.group(3)   # từ sau (sáng/chiều/tối/đêm/giờ)
    return f"{before}{_num_to_word(n)} {after}"


def _convert_bare_number(match: re.Match) -> str:
    """
    Số đứng trơn không rõ ngữ cảnh → chuyển sang chữ
    Chỉ áp dụng cho số 1–59 để tránh xử lý số lạ.
    """
    n = int(match.group(0))
    if 1 <= n <= 59:
        return _num_to_word(n)
    return match.group(0)


# ══════════════════════════════════════════════════════════════════
#  MAIN NORMALIZE FUNCTION
# ══════════════════════════════════════════════════════════════════

# Thứ tự các rule RẤT QUAN TRỌNG — specific trước, generic sau

_RULES: list[tuple[str, object]] = [

    # ── Giờ dạng HH:MM ──────────────────────────────────────────
    # "6:30", "06:30", "22:00"
    (r'\b(\d{1,2}):(\d{2})\b', _convert_time_colon),

    # ── Giờ dạng Xh (viết tắt) ──────────────────────────────────
    # "7h", "10H", "2h30 → xử lý phần :30 bên trên trước"
    # Bắt: "7h" đứng độc lập (không phải "7h30")
    (r'\b(\d{1,2})[hH]\b', _convert_time_h),

    # ── Số + phút ───────────────────────────────────────────────
    # "15 phút", "30 phút"
    (r'\b(\d{1,2})\s*phút\b', _convert_minutes),

    # ── Phần trăm ───────────────────────────────────────────────
    # "50%", "100 %"
    (r'\b(\d{1,3})\s*%', _convert_percent),

    # ── Mức / level ─────────────────────────────────────────────
    # "mức 3", "level 2"
    (r'\b(mức|level)\s+(\d{1,2})\b', _convert_level),

    # ── Số + giờ + buổi / số đứng sau "lúc/vào/đúng" ───────────
    # "6 giờ sáng", "lúc 6 sáng", "vào 8 tối", "đúng 3 chiều"
    (
        r'\b(lúc\s+|vào\s+|đúng\s+|sau\s+)?(\d{1,2})\s+(giờ|sáng|chiều|tối|đêm)\b',
        _convert_standalone_hour,
    ),

    # ── Số đơn còn sót lại (1-59) ───────────────────────────────
    # Chỉ convert số thường gặp trong bối cảnh smart home
    # Bọc boundary để không đụng số trong từ
    (r'(?<!\w)(\d{1,2})(?!\w)', _convert_bare_number),
]

# Compile patterns một lần duy nhất
_COMPILED_RULES = [(re.compile(pattern, re.IGNORECASE), repl) for pattern, repl in _RULES]


def normalize_stt_output(text: str) -> str:
    """
    Chuẩn hóa output STT trước khi đưa vào NLU.

    Args:
        text: Văn bản thô từ PhoWhisper STT

    Returns:
        Văn bản đã chuẩn hóa, phù hợp với format input NLU

    Examples:
        >>> normalize_stt_output("bật đèn lúc 6:30 tối")
        'bật đèn lúc sáu giờ ba mươi tối'

        >>> normalize_stt_output("sau 15 phút tắt quạt phòng ngủ")
        'sau mười lăm phút tắt quạt phòng ngủ'

        >>> normalize_stt_output("đặt báo thức 7h sáng mai")
        'đặt báo thức bảy giờ sáng mai'

        >>> normalize_stt_output("tăng lên 50%")
        'tăng lên năm mươi phần trăm'

        >>> normalize_stt_output("mức 3")
        'mức ba'
    """
    result = text.strip()
    for pattern, repl in _COMPILED_RULES:
        result = pattern.sub(repl, result)
    # Dọn khoảng trắng thừa
    result = re.sub(r'\s{2,}', ' ', result).strip()
    return result


# ══════════════════════════════════════════════════════════════════
#  TEST NHANH
# ══════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    TEST_CASES = [
        # Giờ dạng HH:MM
        ("bật đèn lúc 6:30 tối", "bật đèn lúc sáu giờ ba mươi phút tối"),
        ("đặt báo thức 7:00 sáng mai", "đặt báo thức bảy giờ sáng mai"),
        ("tắt đèn lúc 22:30", "tắt đèn lúc hai mươi hai giờ ba mươi phút"),

        # Giờ dạng Xh
        ("đặt báo thức 7h sáng", "đặt báo thức bảy giờ sáng"),
        ("hủy báo thức 9h sáng nay", "hủy báo thức chín giờ sáng nay"),
        ("tối nay 8h tăng đèn phòng khách", "tối nay tám giờ tăng đèn phòng khách"),

        # Số + phút
        ("sau 15 phút tắt quạt phòng ngủ", "sau mười lăm phút tắt quạt phòng ngủ"),
        ("30 phút nữa khóa cửa", "ba mươi phút nữa khóa cửa"),
        ("10 phút nữa tắt hết đèn", "mười phút nữa tắt hết đèn"),

        # Phần trăm
        ("tăng lên 50%", "tăng lên năm mươi phần trăm"),
        ("giảm xuống 30 %", "giảm xuống ba mươi phần trăm"),

        # Mức
        ("mức 3", "mức ba"),
        ("level 2", "mức hai"),

        # Giờ + buổi
        ("lúc 6 sáng bật đèn", "lúc sáu sáng bật đèn"),
        ("vào 8 tối tắt quạt", "vào tám tối tắt quạt"),
        ("6 giờ rưỡi đánh thức anh dậy", "sáu giờ rưỡi đánh thức anh dậy"),

        # Số đơn
        ("đặt báo thức 6 giờ sáng mai", "đặt báo thức sáu giờ sáng mai"),
        ("7 giờ 15 phút sáng ngày mai", "bảy giờ mười lăm phút sáng ngày mai"),

        # Câu không có số → giữ nguyên
        ("bật đèn phòng ngủ", "bật đèn phòng ngủ"),
        ("tắt hết đèn đi", "tắt hết đèn đi"),
        ("về nhà rồi bật đèn phòng khách", "về nhà rồi bật đèn phòng khách"),
    ]

    print("=" * 65)
    print("  TEST: stt_normalizer")
    print("=" * 65)

    passed = 0
    failed = 0

    for text_in, expected in TEST_CASES:
        result = normalize_stt_output(text_in)
        ok = result == expected
        status = "✅" if ok else "❌"
        print(f"{status}  IN  : {text_in}")
        if not ok:
            print(f"     OUT : {result}")
            print(f"     EXP : {expected}")
        else:
            print(f"     OUT : {result}")
        print()
        if ok:
            passed += 1
        else:
            failed += 1

    print("=" * 65)
    print(f"  Kết quả: {passed}/{passed+failed} passed")
    print("=" * 65)