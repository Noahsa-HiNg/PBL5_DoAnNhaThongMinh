import torch
from transformers import WhisperProcessor, WhisperForConditionalGeneration
import os
os.environ["TRANSFORMERS_OFFLINE"] = "1"
def get_model_and_processor(model_path):
    """
    Hàm nạp mô hình PhoWhisper và Processor lên GPU
    """
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"--- Thiết bị đang sử dụng: {device.upper()} ---")

    print(f"⏳ Đang nạp mô hình từ: {model_path}...")
    
    processor = WhisperProcessor.from_pretrained("vinai/PhoWhisper-base")
    
    # 2. Vẫn load model (trọng số đã fine-tune) từ thư mục local của bạn
    model = WhisperForConditionalGeneration.from_pretrained(
        model_path,
        torch_dtype=torch.float16, 
        device_map="auto"          
    )

    print("✅ Nạp thành công!")
    return model, processor, device