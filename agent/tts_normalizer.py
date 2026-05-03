"""
tts_normalizer.py — Chuẩn hóa text trước khi đưa vào MeloTTS
Xử lý tất cả ký tự/pattern mà TTS tiếng Việt không đọc được,
dựa trên output thực tế của ViT5 từ nlg_dataset_v10.jsonl.

Các pattern được xử lý:
  - °C / °F          → "độ C" / "độ F"
  - %                → "phần trăm"
  - ppm              → "phần triệu"  (CO2)
  - HH:MM  (giờ)    → "HH giờ MM phút" / "HH giờ rưỡi" / "HH giờ"
  - —  (em dash)    → ","
  - ;                → ","
  - CO2              → "CO hai"
  - (  )             → bỏ ngoặc, giữ nội dung

Usage:
    from tts_normalizer import normalize_for_tts

    text = normalize_for_tts("Nhiệt độ 28°C, độ ẩm 72%.")
    # → "Nhiệt độ 28 độ C, độ ẩm 72 phần trăm."

    text = normalize_for_tts("Dạ chừ là 22:00 tối ạ.")
    # → "Dạ chừ là 22 giờ tối ạ."

    text = normalize_for_tts("CO2 850ppm — cao rồi ạ.")
    # → "CO hai 850 phần triệu, cao rồi ạ."
"""

import re


# ─────────────────────────────────────────────────────────────────
#  CÁC HÀM THAY THẾ TỪNG PATTERN
# ─────────────────────────────────────────────────────────────────

def _replace_co2(text: str) -> str:
    """CO2 → CO hai"""
    return re.sub(r'\bCO2\b', 'CO hai', text)


def _replace_temperature(text: str) -> str:
    """28°C → 28 độ C | 16°F → 16 độ F"""
    text = re.sub(r'(\d+(?:[.,]\d+)?)\s*°C', r'\1 độ C', text)
    text = re.sub(r'(\d+(?:[.,]\d+)?)\s*°F', r'\1 độ F', text)
    return text


def _replace_percent(text: str) -> str:
    """72% → 72 phần trăm"""
    return re.sub(r'(\d+(?:[.,]\d+)?)\s*%', r'\1 phần trăm', text)


def _replace_ppm(text: str) -> str:
    """850ppm → 850 phần triệu"""
    return re.sub(r'(\d+)\s*ppm', r'\1 phần triệu', text)


def _replace_time(text: str) -> str:
    """
    HH:MM → tuỳ phút:
      :00  → "HH giờ"
      :30  → "HH giờ rưỡi"
      khác → "HH giờ MM phút"
    Chỉ match giờ hợp lệ 0-23 : 00-59
    """
    def _fmt(m):
        hh = int(m.group(1))
        mm = int(m.group(2))
        if mm == 0:
            return f"{hh} giờ"
        elif mm == 30:
            return f"{hh} giờ rưỡi"
        else:
            return f"{hh} giờ {mm} phút"

    return re.sub(r'\b([01]?\d|2[0-3]):([0-5]\d)\b', _fmt, text)


def _replace_em_dash(text: str) -> str:
    """— (em dash) → , """
    return text.replace('—', ',')


def _replace_semicolon(text: str) -> str:
    """; → ,"""
    return text.replace(';', ',')


def _remove_parentheses(text: str) -> str:
    """(nội dung) → nội dung — bỏ ngoặc, giữ chữ bên trong"""
    prev = None
    while prev != text:
        prev = text
        text = re.sub(r'\(\s*(.*?)\s*\)', r'\1', text)
    return text


def _cleanup_punctuation(text: str) -> str:
    """Dọn dấu câu thừa sinh ra sau các bước thay thế."""
    text = re.sub(r'\s+,', ',', text)       # khoảng trắng trước ,
    text = re.sub(r',\s*,+', ',', text)    # ,, → ,
    text = re.sub(r',\s*\.', '.', text)    # ,. → .
    text = re.sub(r'\s{2,}', ' ', text)    # khoảng trắng thừa
    return text.strip()


# ─────────────────────────────────────────────────────────────────
#  HÀM CHÍNH
# ─────────────────────────────────────────────────────────────────

def normalize_for_tts(text: str) -> str:
    """
    Chuẩn hóa text từ ViT5 output trước khi đưa vào MeloTTS.

    Thứ tự áp dụng:
      1. CO2  (trước các bước số để không bị xung đột)
      2. Nhiệt độ °C / °F
      3. Phần trăm %
      4. ppm
      5. Giờ HH:MM
      6. Em dash —
      7. Dấu chấm phẩy ;
      8. Ngoặc đơn ( )
      9. Dọn dẹp cuối

    Args:
        text: Câu tiếng Việt từ ViT5 generator

    Returns:
        Câu sạch, sẵn sàng đưa vào MeloTTS
    """
    if not text or not text.strip():
        return text

    text = _replace_co2(text)
    text = _replace_temperature(text)
    text = _replace_percent(text)
    text = _replace_ppm(text)
    text = _replace_time(text)
    text = _replace_em_dash(text)
    text = _replace_semicolon(text)
    text = _remove_parentheses(text)
    text = _cleanup_punctuation(text)

    return text


# ─────────────────────────────────────────────────────────────────
#  QUICK TEST
# ─────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    test_cases = [
        # (input, expected_output)

        # --- Nhiệt độ ---
        ("Dạ đo được 34°C, nóng rồi ạ.",
         "Dạ đo được 34 độ C, nóng rồi ạ."),

        # --- Độ ẩm ---
        ("Dạ độ ẩm 78%, hơi cao rồi ạ.",
         "Dạ độ ẩm 78 phần trăm, hơi cao rồi ạ."),

        # --- ppm ---
        ("Dạ CO2 900ppm — cao rồi ạ, nên mở cửa thông thoáng ạ.",
         "Dạ CO hai 900 phần triệu, cao rồi ạ, nên mở cửa thông thoáng ạ."),

        # --- Tổng hợp 3 sensor + dấu ; ---
        ("Dạ cần chú ý: nhiệt 31°C hơi cao; độ ẩm 35% hơi thấp ạ.",
         "Dạ cần chú ý: nhiệt 31 độ C hơi cao, độ ẩm 35 phần trăm hơi thấp ạ."),

        # --- Tổng hợp 3 sensor + em dash ---
        ("Dạ nhiệt 22°C, ẩm 45%, CO2 350ppm — tất cả bình thường ạ.",
         "Dạ nhiệt 22 độ C, ẩm 45 phần trăm, CO hai 350 phần triệu, tất cả bình thường ạ."),

        # --- Ngoặc đơn ---
        ("Dạ chú ý: độ ẩm 90% hơi cao. Còn lại (nhiệt 20°C, CO2 700ppm ổn) ạ.",
         "Dạ chú ý: độ ẩm 90 phần trăm hơi cao. Còn lại nhiệt 20 độ C, CO hai 700 phần triệu ổn ạ."),

        # --- Giờ tròn ---
        ("Dạ chừ là 22:00 tối ạ.",
         "Dạ chừ là 22 giờ tối ạ."),

        # --- Giờ rưỡi ---
        ("Dạ bây giờ là 21:30 tối ạ.",
         "Dạ bây giờ là 21 giờ rưỡi tối ạ."),

        # --- Giờ có phút ---
        ("Dạ chừ là 07:15 sáng ạ.",
         "Dạ chừ là 7 giờ 15 phút sáng ạ."),

        # --- Schedule có % ---
        ("Dạ em đặt hẹn sau 30 phút tăng quạt phòng bếp lên 80% ạ.",
         "Dạ em đặt hẹn sau 30 phút tăng quạt phòng bếp lên 80 phần trăm ạ."),

        # --- Câu bình thường không có ký tự đặc biệt ---
        ("Dạ em bật đèn phòng ngủ rồi ạ.",
         "Dạ em bật đèn phòng ngủ rồi ạ."),
    ]

    print("=" * 65)
    print("  TTS Normalizer — Test Cases")
    print("=" * 65)

    passed = 0
    for raw, expected in test_cases:
        result = normalize_for_tts(raw)
        ok = result == expected
        passed += ok
        status = "✅ PASS" if ok else "❌ FAIL"
        print(f"\n{status}")
        print(f"  Input   : {raw}")
        print(f"  Output  : {result}")
        if not ok:
            print(f"  Expected: {expected}")

    print(f"\n{'=' * 65}")
    print(f"  Kết quả: {passed}/{len(test_cases)} pass")
    print("=" * 65)