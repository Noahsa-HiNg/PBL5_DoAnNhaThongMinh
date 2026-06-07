"""
voice_routers.py — Smart Home Voice/Text API
Tích hợp trực tiếp SmartHomePipeline (không qua HTTP).

3 API:
  POST /api/voice/message  — app gửi text  → trả text phản hồi + transcript
  POST /api/voice/upload   — app gửi audio → PhoWhisper STT → trả text phản hồi + transcript
  POST /api/voice/rpi      — RPi gửi audio → STT → NLU → DM → NLG → TTS → trả WAV về RPi phát loa
"""

import os
import sys
import asyncio
import tempfile
import logging
from pathlib import Path
from functools import partial
from concurrent.futures import ThreadPoolExecutor

import soundfile as sf
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

# Thêm thư mục agent vào sys.path để import pipeline
AGENT_DIR = Path(__file__).resolve().parents[2] / "agent"
sys.path.insert(0, str(AGENT_DIR))

from pipeline import SmartHomePipeline

logger = logging.getLogger(__name__)

# ── Pipeline singleton ───────────────────────────────────────────────
_pipeline: SmartHomePipeline | None = None

# ThreadPoolExecutor riêng cho AI — max_workers=1 vì pipeline không thread-safe
# (CUDA không cho phép 2 request chạy đồng thời, request thứ 2 tự xếp hàng chờ)
_ai_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="ai_pipeline")


def init_pipeline():
    """
    Khởi động pipeline 1 lần duy nhất khi server start.
    - enable_stt=True → PhoWhisper load sẵn lên GPU, dùng cho /upload và /rpi
    - enable_tts=True → MeloTTS load sẵn lên GPU, dùng riêng cho /rpi
      (API /message và /upload gọi process(skip_tts=True) nên không phát loa trên server)
    Gọi hàm này từ lifespan của main.py.
    """
    global _pipeline
    logger.info("🚀 Đang khởi động SmartHomePipeline (STT + NLU + DM + NLG + TTS)...")
    _pipeline = SmartHomePipeline(
        enable_stt=True,  # PhoWhisper — xử lý audio từ app và RPi
        enable_tts=True,  # MeloTTS   — load sẵn, chỉ dùng khi RPi gọi /rpi
    )
    logger.info("✅ Pipeline sẵn sàng!")


# ── Router ───────────────────────────────────────────────────────────
router = APIRouter(prefix="/api/voice", tags=["Giọng nói & Giao tiếp"])


class TextMessageRequest(BaseModel):
    message: str  # Câu lệnh từ app mobile


class TextMessageResponse(BaseModel):
    reply:      str       # Câu phản hồi từ ViT5
    transcript: str = ""  # Text STT (nếu upload audio) hoặc text gốc user gửi


# ── Hàm dùng chung: kiểm tra định dạng ─────────────────────────────

def _check_format(filename: str):
    if not filename.endswith(('.wav', '.flac', '.ogg', '.m4a')):
        raise HTTPException(
            status_code=400,
            detail="Chỉ hỗ trợ định dạng .wav / .flac / .ogg / .m4a"
        )


# ── Hàm dùng chung: đọc + chuẩn hoá audio ──────────────────────────

async def _read_audio(file: UploadFile):
    """Lưu file upload tạm, đọc thành numpy float32 mono 16kHz."""
    suffix = os.path.splitext(file.filename)[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await file.read())
        temp_path = tmp.name

    try:
        audio_array, sample_rate = sf.read(temp_path, dtype='float32')
        if audio_array.ndim > 1:
            audio_array = audio_array[:, 0]
        if sample_rate != 16000:
            import librosa
            audio_array = librosa.resample(
                audio_array, orig_sr=sample_rate, target_sr=16000
            )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Không đọc được file audio: {e}")
    finally:
        os.remove(temp_path)

    return audio_array


# ── API 1: App gửi text → nhận text phản hồi ────────────────────────

@router.post("/message", response_model=TextMessageResponse)
async def send_text_message(request: TextMessageRequest):
    """
    App mobile gửi text → Pipeline xử lý (NLU → DM → ViT5) → trả text + transcript.
    TTS bị bỏ qua (skip_tts=True) — không phát loa trên server.

    Response:
        reply      : Câu phản hồi tiếng Việt
        transcript : Echo lại text user gửi (để app hiển thị bubble chat)
    """
    if _pipeline is None:
        raise HTTPException(status_code=503, detail="Pipeline chưa sẵn sàng.")

    user_text = request.message.strip()
    if not user_text:
        return TextMessageResponse(
            reply="Bạn vừa gửi tin nhắn trống ạ.",
            transcript=""
        )

    loop = asyncio.get_event_loop()
    result: dict = await loop.run_in_executor(
        _ai_executor,
        partial(_pipeline.process, text=user_text, verbose=False, skip_tts=True)
    )

    return TextMessageResponse(
        reply=result["reply"] or "Dạ em chưa hiểu ý anh, anh nói lại được không ạ?",
        transcript=result["transcript"]
    )


# ── API 2: App gửi file audio → PhoWhisper STT → trả text phản hồi ──

@router.post("/upload", response_model=TextMessageResponse)
async def upload_voice(file: UploadFile = File(...)):
    """
    App ghi âm → upload file .wav/.flac/.ogg/.m4a
    → PhoWhisper STT → Pipeline xử lý → trả text phản hồi + transcript STT.
    TTS bị bỏ qua (skip_tts=True) — không phát loa trên server.

    Response:
        reply      : Câu phản hồi tiếng Việt
        transcript : Text nhận diện được từ giọng nói (để app hiển thị bubble chat)
    """
    if _pipeline is None or _pipeline.stt_model is None:
        raise HTTPException(status_code=503, detail="STT chưa sẵn sàng.")

    _check_format(file.filename)
    audio_array = await _read_audio(file)

    loop = asyncio.get_event_loop()
    result: dict = await loop.run_in_executor(
        _ai_executor,
        partial(_pipeline.process, audio_array=audio_array, verbose=False, skip_tts=True)
    )

    return TextMessageResponse(
        reply=result["reply"] or "Dạ em không nghe rõ, anh nói lại được không ạ?",
        transcript=result["transcript"]
    )


# ── API 3: Raspberry Pi gửi audio → nhận audio để phát loa ──────────

@router.post("/rpi")
async def rpi_voice(file: UploadFile = File(...)):
    """
    Raspberry Pi ghi âm → upload file audio
    → STT → NLU → DM → NLG → TTS (MeloTTS đã load sẵn trên GPU, skip_tts=True)
    → sinh WAV riêng → trả về file WAV để RPi phát ra loa.

    Response:
        Content-Type        : audio/wav
        Body                : file WAV chứa câu phản hồi tiếng Việt
        Header X-Transcript : text STT nhận diện được (để debug)
        Header X-Reply      : text phản hồi NLG (để debug)
    """
    if _pipeline is None or _pipeline.stt_model is None:
        raise HTTPException(status_code=503, detail="STT chưa sẵn sàng.")
    if _pipeline.tts is None:
        raise HTTPException(status_code=503, detail="TTS chưa sẵn sàng.")

    _check_format(file.filename)
    audio_array = await _read_audio(file)

    # ── Chạy pipeline STT → NLU → DM → NLG, KHÔNG phát loa trên server
    loop = asyncio.get_event_loop()
    result: dict = await loop.run_in_executor(
        _ai_executor,
        partial(_pipeline.process, audio_array=audio_array, verbose=False, skip_tts=True)
    )

    reply_text: str = (
        result.get("reply") or "Dạ em không nghe rõ, anh nói lại được không ạ."
    )

    # ── TTS: dùng _pipeline.tts đã load sẵn, sinh WAV ra file tạm ───
    output_wav_path = tempfile.mktemp(suffix=".wav")

    def _run_tts():
        from tts_normalizer import normalize_for_tts
        _pipeline.tts._tts.tts_to_file(
            normalize_for_tts(reply_text),
            _pipeline.tts._spk_id,
            output_wav_path,
            speed=_pipeline.tts.speed,
            quiet=True,
        )

    try:
        await loop.run_in_executor(_ai_executor, _run_tts)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"TTS lỗi: {e}")

    # ── Stream WAV về RPi, dọn file tạm sau khi stream xong ──────────
    def _iter_wav():
        try:
            with open(output_wav_path, "rb") as f:
                yield from iter(lambda: f.read(8192), b"")
        finally:
            Path(output_wav_path).unlink(missing_ok=True)

    return StreamingResponse(
        _iter_wav(),
        media_type="audio/wav",
        headers={
            "X-Transcript": result.get("transcript", ""),
            "X-Reply":      reply_text,
        },
    )