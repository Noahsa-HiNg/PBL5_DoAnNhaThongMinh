from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel
import os
import tempfile
import httpx

# ==============================================================================
# CẤU HÌNH NLP SERVER
# Khi có NLP model server, chỉ cần sửa URL này.
# ==============================================================================
NLP_SERVER_URL = "http://localhost:9000/process"
NLP_TIMEOUT_SECONDS = 30.0

# ==============================================================================
# CẤU HÌNH STT (Speech-To-Text)
# ==============================================================================
try:
    import speech_recognition as sr
    SPEECH_RECOGNITION_AVAILABLE = True
except ImportError:
    SPEECH_RECOGNITION_AVAILABLE = False

from core.database import insert_conversation, get_all_conversations

router = APIRouter(prefix="/api/voice", tags=["Giọng nói & Giao tiếp"])


# ---- SCHEMAS ----

class TextMessageRequest(BaseModel):
    message: str    # Văn bản người dùng gửi lên từ mobile


# ==============================================================================
# [HÀM XỬ LÝ CHÍNH - SỬA Ở ĐÂY KHI CÓ MODEL]
#
# Đây là hàm DUY NHẤT cần sửa khi tích hợp NLP model thật.
# Cả API /message (text) và API /upload (voice) đều gọi qua hàm này.
#
# Hiện tại: gọi HTTP đến NLP_SERVER_URL
# Sau này nếu đổi model (Gemini, Rasa, local LLM...): chỉ thay nội dung hàm này
#
# Contract không đổi:
#   - Input:  user_text (str) — câu lệnh từ người dùng
#   - Output: reply (str)     — phản hồi trả về cho người dùng
# ==============================================================================
async def handle_text_command(user_text: str) -> str:
    """
    Xử lý câu lệnh văn bản từ người dùng và trả về phản hồi.

    [SỬA HÀM NÀY KHI CÓ MODEL]
    Hiện tại đang gọi NLP server qua HTTP (httpx async).
    Khi đổi model, chỉ cần thay nội dung bên trong, không cần sửa API.
    """
    # --- BẮT ĐẦU VÙNG THAY THẾ MODEL ---
    try:
        async with httpx.AsyncClient(timeout=NLP_TIMEOUT_SECONDS) as client:
            response = await client.post(
                NLP_SERVER_URL,
                json={"text": user_text}
            )
            response.raise_for_status()
            data = response.json()
            # NLP server trả về JSON dạng: {"reply": "Đã bật đèn thành công."}
            return data.get("reply", "Hệ thống không trả về phản hồi.")
    except httpx.TimeoutException:
        return "Hệ thống xử lý quá lâu, vui lòng thử lại."
    except httpx.ConnectError:
        return "Không thể kết nối đến server xử lý ngôn ngữ."
    except Exception as e:
        return f"Lỗi khi xử lý yêu cầu: {e}"
    # --- KẾT THÚC VÙNG THAY THẾ MODEL ---


# ==============================================================================
# [HÀM CHUYỂN GIỌNG NÓI → VĂN BẢN - SỬA Ở ĐÂY KHI ĐỔI MODEL STT]
#
# Hiện tại: Google Web Speech API (online)
# Có thể đổi sang: Whisper (local), FPT.AI, Vosk (offline)...
#
# Contract không đổi:
#   - Input:  file_path (str) — đường dẫn file âm thanh tạm
#   - Output: text (str)      — văn bản đã nhận diện
# ==============================================================================
def process_voice_stt(file_path: str) -> str:
    """
    Chuyển đổi file âm thanh sang văn bản (Speech-To-Text).

    [SỬA HÀM NÀY KHI ĐỔI MODEL STT]
    Signature không đổi: nhận file_path (str) → trả về text (str).

    Ví dụ đổi sang Whisper:
        import whisper
        model = whisper.load_model("base")
        result = model.transcribe(file_path, language="vi")
        return result["text"]
    """
    if not SPEECH_RECOGNITION_AVAILABLE:
        raise RuntimeError("Chưa cài SpeechRecognition. Chạy: pip install SpeechRecognition")

    # --- BẮT ĐẦU VÙNG THAY THẾ MODEL STT ---
    recognizer = sr.Recognizer()
    with sr.AudioFile(file_path) as source:
        audio_data = recognizer.record(source)
        # Đổi model: xóa dòng dưới, thay bằng logic model mới
        return recognizer.recognize_google(audio_data, language="vi-VN")
    # --- KẾT THÚC VÙNG THAY THẾ MODEL STT ---


# ============================================================
# API 1: Gửi văn bản trực tiếp từ mobile
# ============================================================

@router.post("/message", summary="Gửi text lên server, NLP model xử lý và trả về phản hồi")
async def send_text_message(request: TextMessageRequest):
    """
    Mobile gửi text → handle_text_command() xử lý → trả về phản hồi.
    API này không thay đổi khi đổi model NLP.
    """
    user_text = request.message.strip()
    if not user_text:
        raise HTTPException(status_code=400, detail="Nội dung tin nhắn không được để trống.")

    # Lưu tin nhắn user
    insert_conversation(sender="user", message=user_text)

    # Gọi hàm xử lý trung tâm — SỬA handle_text_command() để đổi model
    system_response = await handle_text_command(user_text)

    # Lưu phản hồi
    insert_conversation(sender="system", message=system_response)

    return {
        "status": "success",
        "user_text": user_text,
        "system_response": system_response
    }


# ============================================================
# API 2: Gửi file âm thanh từ mobile
# ============================================================

@router.post("/upload", summary="Upload file giọng nói, STT → NLP → trả về phản hồi")
async def upload_voice(file: UploadFile = File(...)):
    """
    Mobile upload file âm thanh → process_voice_stt() chuyển thành text
    → handle_text_command() xử lý → trả về phản hồi.
    API này không thay đổi khi đổi model STT hoặc NLP.
    """
    if not file.filename.endswith(('.wav', '.flac', '.aiff')):
        raise HTTPException(status_code=400, detail="Chỉ hỗ trợ .wav, .flac, .aiff")

    # Lưu file tạm
    suffix = os.path.splitext(file.filename)[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await file.read())
        temp_path = tmp.name

    try:
        # Bước 1: Giọng nói → văn bản (SỬA process_voice_stt() để đổi model STT)
        user_text = process_voice_stt(temp_path)

    except sr.UnknownValueError:
        return {"status": "error", "message": "Không thể nhận diện giọng nói."}
    except sr.RequestError as e:
        return {"status": "error", "message": f"Lỗi dịch vụ STT: {e}"}
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        os.remove(temp_path)   # luôn xóa file tạm dù có lỗi hay không

    # Lưu câu lệnh của user
    insert_conversation(sender="user", message=user_text)

    # Bước 2: Văn bản → xử lý lệnh (SỬA handle_text_command() để đổi model NLP)
    system_response = await handle_text_command(user_text)

    # Lưu phản hồi
    insert_conversation(sender="system", message=system_response)

    return {
        "status": "success",
        "user_text": user_text,
        "system_response": system_response
    }


# ============================================================
# API 3: Lấy lịch sử hội thoại
# ============================================================

@router.get("/conversations", summary="Lấy toàn bộ lịch sử cuộc hội thoại")
async def get_conversations(limit: int = 100):
    conversations = get_all_conversations(limit=limit)
    return {
        "status": "success",
        "data": conversations
    }
