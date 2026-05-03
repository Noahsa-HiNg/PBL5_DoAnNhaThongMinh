import os
import torch
import sounddevice as sd
import numpy as np

# Nhập hàm nạp model từ file của bạn
from load_model_stt import get_model_and_processor 

# --- CẤU HÌNH ĐƯỜNG DẪN TỰ ĐỘNG ---
# Lấy tự động thư mục đang chứa file code này (thư mục 'agent')
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Ghép tên thư mục chứa model vào (Đã cập nhật thêm thư mục "model")
MODEL_DIR = os.path.join(BASE_DIR, "model", "PhoWhisper_Base_Finetuned_V2") 

# --- CẤU HÌNH THU ÂM ---
SAMPLE_RATE = 16000
DURATION = 5  # Thời gian thu âm mỗi lượt (giây)

def record_audio(duration, fs):
    """Hàm thu âm trực tiếp từ microphone"""
    print(f"\n👉 Nhấn Enter để BẮT ĐẦU thu âm ({duration} giây)...", end="")
    input()
    print("🎙️ Đang thu âm... Hãy nói câu lệnh của bạn!")
    
    # Thu âm dạng float32, mono (1 channel)
    recording = sd.rec(int(duration * fs), samplerate=fs, channels=1, dtype='float32')
    sd.wait()  # Block code ở đây cho đến khi thu âm xong
    print("✅ Đã thu âm xong!")
    
    # Trả về mảng 1D cho numpy
    return recording.squeeze()

def run_live_test():
    print("="*60)
    print("🎤 KHỞI ĐỘNG CÔNG CỤ TEST STT TRỰC TIẾP (PHOWHISPER)")
    print("="*60)

    if not os.path.exists(MODEL_DIR):
        print(f"❌ LỖI: Không tìm thấy thư mục model tại:\n   {MODEL_DIR}")
        print("Vui lòng kiểm tra lại tên thư mục chứa mô hình.")
        return

    # Nạp mô hình PhoWhisper và Processor lên GPU
    model, processor, device = get_model_and_processor(MODEL_DIR)

    # Vòng lặp test liên tục
    while True:
        # 1. Thu âm trực tiếp
        audio_array = record_audio(DURATION, SAMPLE_RATE)

        # 2. Chuẩn bị input cho model
        input_features = processor(
            audio_array, 
            sampling_rate=SAMPLE_RATE, 
            return_tensors="pt"
        ).input_features.to(device, dtype=torch.float16)

        # 3. Cấu hình tiếng Việt cho decoder
        forced_ids = processor.get_decoder_prompt_ids(language="vi", task="transcribe")

        print(f"⚙️ Đang phân tích và nhận diện giọng nói...")
        try:
            with torch.no_grad():
                predicted_ids = model.generate(
                    input_features, 
                    forced_decoder_ids=forced_ids,
                    max_length=448 # Độ dài tối đa của câu
                )
            
            # 4. Giải mã IDs thành văn bản
            transcription = processor.batch_decode(predicted_ids, skip_special_tokens=True)[0]

            print("\n" + "="*50)
            print(f"📝 KẾT QUẢ NHẬN DIỆN: {transcription}")
            print("="*50)
            
        except RuntimeError as e:
            if "CUDA out of memory" in str(e):
                print("\n❌ LỖI TRÀN VRAM (CUDA Out of Memory)!")
                print("💡 Cách khắc phục: Hãy tắt Ollama đang chạy ngầm trên máy của bạn để giải phóng VRAM cho con AI này nhé.")
            else:
                print(f"\n❌ Lỗi hệ thống: {e}")
        except Exception as e:
            print(f"\n❌ Lỗi khi xử lý model: {e}")

        # Hỏi người dùng có muốn tiếp tục không
        cont = input("\n🔁 Bạn có muốn test câu khác không? (y/n/enter=Có): ").strip().lower()
        if cont not in ['', 'y', 'yes', 'có', 'co']:
            print("👋 Đã thoát trình test STT.")
            break

if __name__ == "__main__":
    run_live_test()