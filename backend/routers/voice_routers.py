"""
voice_routers.py — Smart Home Voice/Text API
"""

import os
import sys
import asyncio
import tempfile
import logging
from pathlib import Path
from functools import partial

import numpy as np
import soundfile as sf
from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel

AGENT_DIR = Path(__file__).resolve().parents[2] / "agent"
sys.path.insert(0, str(AGENT_DIR))

from pipeline import SmartHomePipeline

logger = logging.getLogger(__name__)

_pipeline: SmartHomePipeline | None = None

# ThreadPoolExecutor riêng cho AI — tránh tranh chấp với default executor
from concurrent.futures import ThreadPoolExecutor
_ai_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="ai_pipeline")


def init_pipeline():
    global _pipeline
    logger.info("🚀 Đang khởi động SmartHomePipeline...")
    _pipeline = SmartHomePipeline(
        enable_stt=True,
        enable_tts=False,
    )
    logger.info("✅ Pipeline sẵn sàng!")


router = APIRouter(prefix="/api/voice", tags=["Giọng nói & Giao tiếp"])


class TextMessageRequest(BaseModel):
    message: str

class TextMessageResponse(BaseModel):
    reply: str


@router.post("/message", response_model=TextMessageResponse)
async def send_text_message(request: TextMessageRequest):
    user_text = request.message.strip()
    if not user_text:
        return TextMessageResponse(reply="Bạn vừa gửi tin nhắn trống ạ.")

    loop = asyncio.get_event_loop()
    reply = await loop.run_in_executor(
        _ai_executor,
        partial(_pipeline.process, text=user_text, verbose=False)
    )

    if not reply:
        reply = "Dạ em chưa hiểu ý anh, anh nói lại được không ạ?"

    return TextMessageResponse(reply=reply)


@router.post("/upload", response_model=TextMessageResponse)
async def upload_voice(file: UploadFile = File(...)):
    if _pipeline is None or _pipeline.stt_model is None:
        raise HTTPException(status_code=503, detail="STT chưa sẵn sàng.")

    if not file.filename.endswith(('.wav', '.flac', '.ogg', '.m4a')):
        raise HTTPException(status_code=400, detail="Chỉ hỗ trợ .wav / .flac / .ogg / .m4a")

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
            audio_array = librosa.resample(audio_array, orig_sr=sample_rate, target_sr=16000)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Không đọc được file audio: {e}")
    finally:
        os.remove(temp_path)

    loop = asyncio.get_event_loop()
    reply = await loop.run_in_executor(
        _ai_executor,
        partial(_pipeline.process, audio_array=audio_array, verbose=False)
    )

    if not reply:
        reply = "Dạ em không nghe rõ, anh nói lại được không ạ?"

    return TextMessageResponse(reply=reply)