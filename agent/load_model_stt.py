import torch
from transformers import WhisperProcessor, WhisperForConditionalGeneration

def get_model_and_processor(model_path):
    """
    Hàm nạp mô hình PhoWhisper và Processor lên GPU
    """
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"--- Thiết bị đang sử dụng: {device.upper()} ---")

    print(f"⏳ Đang nạp mô hình từ: {model_path}...")
    
    # 1. SỬA Ở ĐÂY: Load processor trực tiếp từ model gốc của VinAI trên mạng
    processor = WhisperProcessor.from_pretrained("vinai/PhoWhisper-base")
    
    # 2. Vẫn load model (trọng số đã fine-tune) từ thư mục local của bạn
    model = WhisperForConditionalGeneration.from_pretrained(
        model_path,
        torch_dtype=torch.float16, 
        device_map="auto"          
    )

    print("✅ Nạp thành công!")
    return model, processor, device