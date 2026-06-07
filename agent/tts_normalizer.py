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
from num2words import num2words


# ─────────────────────────────────────────────────────────────────
#  CÁC HÀM THAY THẾ TỪNG PATTERN
# ─────────────────────────────────────────────────────────────────

def _num_to_vi(n_str: str) -> str:
    """Chuyển chuỗi số (int hoặc float) → chữ tiếng Việt.
    Ví dụ: '30' → 'ba mươi', '28.5' → 'hai mươi tám phẩy năm'
    """
    try:
        # Thử int trước
        if '.' not in n_str and ',' not in n_str:
            return num2words(int(n_str), lang='vi')
        # Float: chuẩn hóa dấu phẩy → chấm rồi đọc
        val = float(n_str.replace(',', '.'))
        return num2words(val, lang='vi')
    except Exception:
        return n_str  # fallback: giữ nguyên nếu lỗi


def _replace_numbers(text: str) -> str:
    """Thay toàn bộ số standalone → chữ tiếng Việt.
    Chỉ replace số đứng độc lập (không dính vào chữ), ví dụ:
      '30' → 'ba mươi'
      '75' → 'bảy mươi lăm'
    Số đã được xử lý bởi các pattern trước (°C, %, ppm, HH:MM)
    đã thành chữ rồi nên không bị match lại.
    """
    def _repl(m):
        return _num_to_vi(m.group(0))
    # Match số nguyên hoặc thập phân (dấu chấm hoặc phẩy)
    return re.sub(r'\b\d+(?:[.,]\d+)?\b', _repl, text)


def _replace_co2(text: str) -> str:
    """CO2 → CO hai"""
    return re.sub(r'\bCO2\b', 'CO hai', text)


def _replace_temperature(text: str) -> str:
    """28°C → 'hai mươi tám độ xê' | 28C → tương tự
    Dùng 'độ xê' thay vì 'độ C' vì MeloTTS đọc chữ 'C' thành 'xê' không chuẩn,
    nên viết thẳng phiên âm để TTS đọc đúng.
    """
    text = re.sub(r'(\d+(?:[.,]\d+)?)\s*°C', r'\1 độ xê', text)
    text = re.sub(r'(\d+(?:[.,]\d+)?)\s*°F', r'\1 độ ép-phờ', text)
    text = re.sub(r'(\d+(?:[.,]\d+)?)\s*C\b', r'\1 độ xê', text)
    text = re.sub(r'(\d+(?:[.,]\d+)?)\s*F\b', r'\1 độ ép-phờ', text)
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
      2. Nhiệt độ °C / °F / C / F  → "XX độ"
      3. Phần trăm %               → "XX phần trăm"
      4. ppm                       → "XX phần triệu"
      5. Giờ HH:MM                 → "XX giờ ..."
      6. Em dash —                 → ","
      7. Dấu chấm phẩy ;          → ","
      8. Ngoặc đơn ( )             → bỏ ngoặc
      9. Số còn lại                → chữ tiếng Việt (num2words)
     10. Dọn dẹp cuối

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
    text = _replace_numbers(text)   # convert số còn lại → chữ
    text = _cleanup_punctuation(text)

    return text


# ─────────────────────────────────────────────────────────────────
#  QUICK TEST
# ─────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    test_cases = [
        # (input, expected_output)

        # --- Nhiệt độ KHÔNG có ký tự ° (ViT5 đôi khi bỏ mất) ---
        ("Dạ nhiệt độ 30C, bình thường ạ.",
         "Dạ nhiệt độ ba mươi độ xê, bình thường ạ."),

        ("Dạ nhiệt 28.5C, độ ẩm 75%, bình thường ạ.",
         "Dạ nhiệt hai mươi tám phẩy năm mươi độ xê, độ ẩm bảy mươi lăm phần trăm, bình thường ạ."),

        # --- Nhiệt độ có ° ---
        ("Dạ đo được 34°C, nóng rồi ạ.",
         "Dạ đo được ba mươi bốn độ xê, nóng rồi ạ."),

        # --- Độ ẩm ---
        ("Dạ độ ẩm 78%, hơi cao rồi ạ.",
         "Dạ độ ẩm bảy mươi tám phần trăm, hơi cao rồi ạ."),

        # --- ppm ---
        ("Dạ CO2 900ppm — cao rồi ạ, nên mở cửa thông thoáng ạ.",
         "Dạ CO hai chín trăm phần triệu, cao rồi ạ, nên mở cửa thông thoáng ạ."),

        # --- Tổng hợp 3 sensor + dấu ; ---
        ("Dạ cần chú ý: nhiệt 31°C hơi cao; độ ẩm 35% hơi thấp ạ.",
         "Dạ cần chú ý: nhiệt ba mươi mốt độ xê hơi cao, độ ẩm ba mươi lăm phần trăm hơi thấp ạ."),

        # --- Tổng hợp 3 sensor + em dash ---
        ("Dạ nhiệt 22°C, ẩm 45%, CO2 350ppm — tất cả bình thường ạ.",
         "Dạ nhiệt hai mươi hai độ xê, ẩm bốn mươi lăm phần trăm, CO hai ba trăm năm mươi phần triệu, tất cả bình thường ạ."),

        # --- Ngoặc đơn ---
        ("Dạ chú ý: độ ẩm 90% hơi cao. Còn lại (nhiệt 20°C, CO2 700ppm ổn) ạ.",
         "Dạ chú ý: độ ẩm chín mươi phần trăm hơi cao. Còn lại nhiệt hai mươi độ xê, CO hai bảy trăm phần triệu ổn ạ."),

        # --- Giờ tròn ---
        ("Dạ chừ là 22:00 tối ạ.",
         "Dạ chừ là hai mươi hai giờ tối ạ."),

        # --- Giờ rưỡi ---
        ("Dạ bây giờ là 21:30 tối ạ.",
         "Dạ bây giờ là hai mươi mốt giờ rưỡi tối ạ."),

        # --- Giờ có phút ---
        ("Dạ chừ là 07:15 sáng ạ.",
         "Dạ chừ là bảy giờ mười lăm phút sáng ạ."),

        # --- Schedule có % ---
        ("Dạ em đặt hẹn sau 30 phút tăng quạt phòng bếp lên 80% ạ.",
         "Dạ em đặt hẹn sau ba mươi phút tăng quạt phòng bếp lên tám mươi phần trăm ạ."),

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