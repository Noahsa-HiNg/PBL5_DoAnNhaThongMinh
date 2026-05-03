"""
voice_routers.py — Smart Home Voice/Text API
Tích hợp trực tiếp SmartHomePipeline (không qua HTTP).

2 API:
  POST /api/voice/message  — app gửi text  → trả text phản hồi + transcript
  POST /api/voice/upload   — app gửi audio → PhoWhisper STT → trả text phản hồi + transcript
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
    Khởi động pipeline 1 lần duy nhất.
    Gọi hàm này từ lifespan của main.py.
    """
    global _pipeline
    logger.info("🚀 Đang khởi động SmartHomePipeline...")
    _pipeline = SmartHomePipeline(
        enable_stt=True,   # Bật PhoWhisper để xử lý audio từ app
        enable_tts=False,  # Chỉ trả text về app, không phát loa
    )
    logger.info("✅ Pipeline sẵn sàng!")


# ── Router ───────────────────────────────────────────────────────────
router = APIRouter(prefix="/api/voice", tags=["Giọng nói & Giao tiếp"])


class TextMessageRequest(BaseModel):
    message: str  # Câu lệnh từ app mobile


class TextMessageResponse(BaseModel):
    reply:      str       # Câu phản hồi từ ViT5
    transcript: str = ""  # Text STT (nếu upload audio) hoặc text gốc user gửi


# ── API 1: App gửi text → nhận text phản hồi ────────────────────────

@router.post("/message", response_model=TextMessageResponse)
async def send_text_message(request: TextMessageRequest):
    """
    App mobile gửi text → Pipeline xử lý (NLU → DM → ViT5) → trả text + transcript.

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
        partial(_pipeline.process, text=user_text, verbose=False)
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

    Response:
        reply      : Câu phản hồi tiếng Việt
        transcript : Text nhận diện được từ giọng nói (để app hiển thị bubble chat)
    """
    if _pipeline is None or _pipeline.stt_model is None:
        raise HTTPException(status_code=503, detail="STT chưa sẵn sàng.")

    if not file.filename.endswith(('.wav', '.flac', '.ogg', '.m4a')):
        raise HTTPException(
            status_code=400,
            detail="Chỉ hỗ trợ định dạng .wav / .flac / .ogg / .m4a"
        )

    # Lưu file tạm
    suffix = os.path.splitext(file.filename)[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await file.read())
        temp_path = tmp.name

    try:
        # Đọc audio → numpy array float32
        audio_array, sample_rate = sf.read(temp_path, dtype='float32')

        # Nếu stereo thì lấy kênh đầu
        if audio_array.ndim > 1:
            audio_array = audio_array[:, 0]

        # Resample về 16kHz nếu app gửi sample rate khác
        if sample_rate != 16000:
            import librosa
            audio_array = librosa.resample(
                audio_array, orig_sr=sample_rate, target_sr=16000
            )

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Không đọc được file audio: {e}")
    finally:
        os.remove(temp_path)

    # Đưa audio vào pipeline trong executor — không block event loop
    loop = asyncio.get_event_loop()
    result: dict = await loop.run_in_executor(
        _ai_executor,
        partial(_pipeline.process, audio_array=audio_array, verbose=False)
    )

    return TextMessageResponse(
        reply=result["reply"] or "Dạ em không nghe rõ, anh nói lại được không ạ?",
        transcript=result["transcript"]
    )