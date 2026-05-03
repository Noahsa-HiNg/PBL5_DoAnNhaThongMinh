"""
test_api.py — Test API Smart Home trực tiếp trên máy
Nhấn Enter → thu âm 3 giây → gọi API /upload
Nhập text   → gọi API /message

Chạy: python test_api.py
"""

import requests
import tempfile
import os
import sounddevice as sd
import soundfile as sf
import numpy as np

# ── Cấu hình ────────────────────────────────────────────
API_BASE    = "http://172.20.10.5:8000/api/voice"
SAMPLE_RATE = 16000
DURATION    = 3   # giây thu âm
# ────────────────────────────────────────────────────────


def call_text_api(text: str) -> str:
    """Gọi POST /message với text."""
    res = requests.post(
        f"{API_BASE}/message",
        json={"message": text},
        timeout=30,
    )
    res.raise_for_status()
    return res.json()["reply"]


def call_voice_api(audio_array: np.ndarray) -> str:
    """Gọi POST /upload với file wav."""
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        tmp_path = f.name

    try:
        sf.write(tmp_path, audio_array, SAMPLE_RATE)
        with open(tmp_path, "rb") as f:
            res = requests.post(
                f"{API_BASE}/upload",
                files={"file": ("recording.wav", f, "audio/wav")},
                timeout=60,
            )
        res.raise_for_status()
        return res.json()["reply"]
    finally:
        os.remove(tmp_path)


def record_audio() -> np.ndarray:
    """Thu âm DURATION giây từ mic."""
    print(f"🎙️  Đang thu âm {DURATION} giây... Hãy nói!")
    audio = sd.rec(
        int(DURATION * SAMPLE_RATE),
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype="float32",
    )
    sd.wait()
    print("✅ Xong!")
    return audio.squeeze()


def main():
    print("=" * 50)
    print("  🏠 Smart Home API Tester")
    print("=" * 50)
    print("  [Enter]      → Thu âm 3 giây rồi gửi")
    print("  [Nhập text]  → Gửi text thẳng lên API")
    print("  [quit]       → Thoát")
    print("=" * 50)
    if True:
        try:
            user_input = input("\n👤 Bạn: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nTạm biệt!")
            #break

        if user_input.lower() in ("quit", "exit", "q"):
            print("Tạm biệt!")
            #break

        try:
            if user_input == "":
                # Nhấn Enter → thu âm
                audio = record_audio()
                reply = call_voice_api(audio)
            else:
                # Nhập text → gọi thẳng
                reply = call_text_api(user_input)

            print(f"🤖 Bot: {reply}")

        except requests.ConnectionError:
            print("❌ Không kết nối được server. Kiểm tra uvicorn đang chạy chưa.")
        except requests.Timeout:
            print("❌ Server xử lý quá lâu (timeout 30s).")
        except Exception as e:
            print(f"❌ Lỗi: {e}")


if __name__ == "__main__":
    main()