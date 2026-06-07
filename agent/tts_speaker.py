"""
tts_speaker.py — Wrapper cho MeloTTS Vietnamese
Tích hợp vào Smart Home Pipeline (luôn đọc, cuda, blocking)
"""
import os
os.environ["TRANSFORMERS_OFFLINE"] = "1"
import logging
import subprocess
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)

# ── Đường dẫn model MeloTTS ────────────────────────────────────────
_BASE = Path(r"E:\SV\Ki6\PBL5\PBL5_DoAnNhaThongMinh\agent\MeloTTS_Vietnamese-main\models")
TTS_CONFIG_PATH = str(_BASE / "config.json")
TTS_CKPT_PATH   = str(_BASE / "G_463000.pth")


class TTSSpeaker:
    """
    Wrapper MeloTTS Vietnamese — sinh audio và phát blocking.

    Usage:
        speaker = TTSSpeaker()
        speaker.speak("Đã bật đèn phòng khách rồi ạ.")
    """

    def __init__(
        self,
        config_path: str = TTS_CONFIG_PATH,
        ckpt_path:   str = TTS_CKPT_PATH,
        device:      str = "cuda",
        speed:       float = 1.0,
    ):
        self.speed  = speed
        self.device = device

        logger.info("🔄 Loading MeloTTS Vietnamese...")
        try:
            from melo.api import TTS
            self._tts = TTS(
                language="VI",
                device=device,
                config_path=config_path,
                ckpt_path=ckpt_path,
            )
            # Lấy speaker_id đầu tiên (mặc định)
            speaker_ids    = self._tts.hps.data.spk2id
            self._spk_id   = list(speaker_ids.values())[0]
            logger.info(f"✅ MeloTTS loaded | speakers: {speaker_ids} | device: {device}")
        except Exception as e:
            logger.error(f"❌ Không load được MeloTTS: {e}")
            raise

    def speak(self, text: str) -> None:
        """
        Sinh audio từ text rồi phát blocking (chờ xong mới return).

        Args:
            text: Câu tiếng Việt cần đọc
        """
        if not text or not text.strip():
            return

        # Dùng tempfile để không cần quản lý output.wav thủ công
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            wav_path = f.name

        try:
            # Sinh audio
            self._tts.tts_to_file(
                text,
                self._spk_id,
                wav_path,
                speed=self.speed,
                quiet=True,
            )
            # Phát audio — blocking
            _play_wav_blocking(wav_path)

        except Exception as e:
            logger.error(f"❌ TTS lỗi khi đọc: '{text}' — {e}")
        finally:
            # Dọn file tạm
            try:
                Path(wav_path).unlink(missing_ok=True)
            except Exception:
                pass


def _play_wav_blocking(wav_path: str) -> None:
    """
    Phát file WAV blocking. Tự chọn backend theo OS.
    Windows → PowerShell SoundPlayer
    Linux   → aplay (Raspberry Pi)
    """
    import platform
    os_name = platform.system()

    if os_name == "Windows":
        # PowerShell SoundPlayer — không cần cài thêm
        script = (
            f"(New-Object Media.SoundPlayer '{wav_path}').PlaySync()"
        )
        subprocess.run(
            ["powershell", "-Command", script],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    elif os_name == "Linux":
        # aplay có sẵn trên Raspberry Pi OS
        subprocess.run(
            ["aplay", wav_path],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    else:
        logger.warning(f"⚠️ OS '{os_name}' chưa hỗ trợ auto-play, file WAV tại: {wav_path}")