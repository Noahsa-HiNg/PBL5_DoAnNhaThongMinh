"""
pipeline.py — Smart Home Pipeline hoàn chỉnh
STT (PhoWhisper) → Normalize → NLU (micro-BERT) → Dialog Manager → API → NLG (ViT5) → Normalize → TTS (MeloTTS)

Usage:
    python pipeline.py                        # chế độ tương tác, thu âm mic
    python pipeline.py --no-stt               # tắt STT, nhập text bàn phím
    python pipeline.py --no-tts               # tắt TTS
    python pipeline.py --no-stt --no-tts      # thuần text (debug)
    python pipeline.py --text "bật đèn"       # chạy 1 câu text rồi thoát
    python pipeline.py --duration 7           # thu âm 7 giây mỗi lượt (mặc định 5)
"""

import logging
import torch
import numpy as np
import os

# ── Cấu hình logging ───────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
)
logger = logging.getLogger(__name__)

# ── Import các thành phần ──────────────────────────────────────────
from inference        import load_model, predict
from api_client       import SmartHomeAPIClient
from dialog_manager   import SmartHomeDialogManager
from vit5_generator   import ViT5Generator
from tts_speaker      import TTSSpeaker
from tts_normalizer   import normalize_for_tts
from stt_normalizer   import normalize_stt_output
from load_model_stt   import get_model_and_processor
from config           import NLU_THRESHOLD

# STT config
STT_SAMPLE_RATE = 16000


# ─────────────────────────────────────────────
#  CLARIFY TEMPLATES  (không qua ViT5)
# ─────────────────────────────────────────────
CLARIFY_TEMPLATES = {
    'light': {
        'on':       'Dạ anh muốn bật đèn phòng nào ạ? Phòng khách, phòng ngủ, phòng bếp hay sân?',
        'off':      'Dạ anh muốn tắt đèn phòng nào ạ? Phòng khách, phòng ngủ, phòng bếp hay sân?',
        'adj_up':   'Dạ tăng đèn phòng nào ạ? Phòng khách, phòng ngủ, phòng bếp hay sân?',
        'adj_down': 'Dạ giảm đèn phòng nào ạ? Phòng khách, phòng ngủ, phòng bếp hay sân?',
        'default':  'Dạ anh muốn điều chỉnh đèn phòng nào ạ?',
    },
    'fan': {
        'on':       'Dạ anh muốn bật quạt phòng nào ạ? Phòng khách, phòng ngủ hay phòng bếp?',
        'off':      'Dạ anh muốn tắt quạt phòng nào ạ? Phòng khách, phòng ngủ hay phòng bếp?',
        'adj_up':   'Dạ tăng quạt phòng nào ạ? Phòng khách, phòng ngủ hay phòng bếp?',
        'adj_down': 'Dạ giảm quạt phòng nào ạ? Phòng khách, phòng ngủ hay phòng bếp?',
        'default':  'Dạ anh muốn điều chỉnh quạt phòng nào ạ?',
    },
    'default': 'Dạ anh muốn điều khiển thiết bị ở phòng nào ạ?',
}


def _clarify_response(dm_output: str) -> str:
    """Sinh câu hỏi lại từ __clarify__ output — không qua ViT5."""
    action = ''
    device = ''
    for part in dm_output.split('|'):
        part = part.strip()
        if part.startswith('action='):
            action = part[7:]
        elif part.startswith('device='):
            device = part[7:]

    device_tpl = CLARIFY_TEMPLATES.get(device)
    if device_tpl:
        if isinstance(device_tpl, dict):
            return device_tpl.get(action, device_tpl['default'])
        return device_tpl
    return CLARIFY_TEMPLATES['default']


# ─────────────────────────────────────────────
#  MAIN PIPELINE CLASS
# ─────────────────────────────────────────────

class SmartHomePipeline:
    """
    Pipeline hoàn chỉnh:
      STT (PhoWhisper) → stt_normalizer
        → NLU (micro-BERT) → Dialog Manager → API
        → NLG (ViT5) → tts_normalizer → TTS (MeloTTS)

    Args:
        api_base_url : URL API server (mặc định localhost:5000)
        enable_stt   : Bật/tắt STT — tắt thì nhập text thẳng (mặc định True)
        enable_tts   : Bật/tắt TTS (mặc định True)
        stt_model_dir: Đường dẫn thư mục chứa PhoWhisper fine-tuned
        stt_duration : Thời gian thu âm mỗi lượt (giây, mặc định 5)
    """

    def __init__(
        self,
        api_base_url  : str  = None,
        enable_stt    : bool = True,
        enable_tts    : bool = True,
        stt_model_dir : str  = None,
        stt_duration  : int  = 3,
    ):
        logger.info("=" * 55)
        logger.info("  🏠 Khởi động Smart Home Pipeline")
        logger.info("=" * 55)

        self.stt_duration = stt_duration

        # ── Bước 0: Load STT ──────────────────────────────────────
        self.stt_model     = None
        self.stt_processor = None
        self.stt_device    = None

        if enable_stt:
            if stt_model_dir is None:
                _base = os.path.dirname(os.path.abspath(__file__))
                stt_model_dir = os.path.join(
                    _base, 'model', 'PhoWhisper_Base_Finetuned_V2'
                )

            if not os.path.exists(stt_model_dir):
                logger.warning(
                    f"⚠️ Không tìm thấy model STT tại: {stt_model_dir}\n"
                    "   STT bị tắt — chuyển sang chế độ nhập text."
                )
            else:
                logger.info(f"🎤 [0/4] Loading PhoWhisper STT từ: {stt_model_dir}")
                try:
                    self.stt_model, self.stt_processor, self.stt_device = \
                        get_model_and_processor(stt_model_dir)
                    logger.info("✅ STT sẵn sàng!")
                except Exception as e:
                    logger.warning(f"⚠️ STT không khởi động được, bỏ qua: {e}")
        else:
            logger.info("🔇 [0/4] STT bị tắt (--no-stt)")

        # ── Bước 1: Load NLU ──────────────────────────────────────
        logger.info("📦 [1/4] Loading micro-BERT NLU...")
        self.nlu_model, self.sp, self.device = load_model()

        # ── Bước 2: Setup API + Dialog Manager ────────────────────
        logger.info("🔌 [2/4] Khởi tạo API Client + Dialog Manager...")
        kwargs   = {'base_url': api_base_url} if api_base_url else {}
        self.api = SmartHomeAPIClient(**kwargs)
        self.dm  = SmartHomeDialogManager(api_client=self.api)

        # ── Bước 3: Load NLG ──────────────────────────────────────
        logger.info("📦 [3/4] Loading ViT5 NLG...")
        self.nlg = ViT5Generator(device=self.device)

        # ── Bước 4: Load TTS ──────────────────────────────────────
        self.tts: TTSSpeaker | None = None
        if enable_tts:
            logger.info("🔊 [4/4] Loading MeloTTS...")
            try:
                self.tts = TTSSpeaker(device=str(self.device))
            except Exception as e:
                logger.warning(f"⚠️ TTS không khởi động được, bỏ qua: {e}")
        else:
            logger.info("🔇 [4/4] TTS bị tắt (--no-tts)")

        # ── Log VRAM sau khi load xong ────────────────────────────
        if torch.cuda.is_available():
            allocated = torch.cuda.memory_allocated() / 1024**3
            total     = torch.cuda.get_device_properties(0).total_memory / 1024**3
            logger.info(f"🖥️  VRAM: {allocated:.2f}GB / {total:.2f}GB sau khi load models")

        logger.info("✅ Pipeline sẵn sàng!\n")

    # ─────────────────────────────────────────────────────────────
    #  STT: thu âm + nhận diện
    # ─────────────────────────────────────────────────────────────

    def _record_audio(self) -> np.ndarray:
        """Thu âm từ microphone, trả về mảng float32 1D."""
        import sounddevice as sd
        print(
            f"\n👉 Nhấn Enter để BẮT ĐẦU thu âm ({self.stt_duration} giây)...",
            end="",
        )
        input()
        print("🎙️  Đang thu âm... Hãy nói câu lệnh!")
        recording = sd.rec(
            int(self.stt_duration * STT_SAMPLE_RATE),
            samplerate=STT_SAMPLE_RATE,
            channels=1,
            dtype='float32',
        )
        sd.wait()
        print("✅ Xong!")
        return recording.squeeze()

    def _transcribe(self, audio_array: np.ndarray) -> tuple[str, str]:
        """
        Chạy PhoWhisper trên audio_array.
        Trả về (raw_text, normalized_text).
        """
        if self.stt_model is None:
            raise RuntimeError("STT chưa được khởi động.")

        input_features = self.stt_processor(
            audio_array,
            sampling_rate=STT_SAMPLE_RATE,
            return_tensors="pt",
        ).input_features.to(self.stt_device, dtype=torch.float16)

        forced_ids = self.stt_processor.get_decoder_prompt_ids(
            language="vi", task="transcribe"
        )

        with torch.no_grad():
            predicted_ids = self.stt_model.generate(
                input_features,
                forced_decoder_ids=forced_ids,
                max_length=448,
            )

        raw_text = self.stt_processor.batch_decode(
            predicted_ids, skip_special_tokens=True
        )[0].strip()

        normalized_text = normalize_stt_output(raw_text)
        return raw_text, normalized_text

    # ─────────────────────────────────────────────────────────────
    #  PROCESS: xử lý một lượt hội thoại
    # ─────────────────────────────────────────────────────────────

    def process(
        self,
        text        : str  = None,
        audio_array : np.ndarray = None,
        verbose     : bool = True,
        skip_tts    : bool = False,
    ) -> dict:
        """
        Xử lý một câu lệnh. Nhận text hoặc audio_array (không cần cả hai).

        Ưu tiên: nếu audio_array được truyền vào thì dùng STT;
                 nếu text được truyền thì bỏ qua STT.

        Args:
            text        : Câu lệnh text (dùng khi STT tắt hoặc test)
            audio_array : Mảng audio float32 16kHz từ microphone
            verbose     : In chi tiết từng bước
            skip_tts    : Bỏ qua bước phát TTS (dùng khi caller tự xử lý audio)

        Returns:
            dict với 2 key:
                "reply"      : Câu phản hồi tiếng Việt từ ViT5
                "transcript" : Text STT (nếu dùng audio) hoặc text gốc user gửi
        """
        stt_raw        = None
        stt_normalized = None

        # ── Bước 0: STT (nếu có audio) ────────────────────────────
        if audio_array is not None and self.stt_model is not None:
            try:
                stt_raw, stt_normalized = self._transcribe(audio_array)
                text = stt_normalized
            except RuntimeError as e:
                if "CUDA out of memory" in str(e):
                    logger.error("❌ VRAM tràn! Hãy tắt Ollama hoặc giảm tải GPU.")
                else:
                    logger.error(f"❌ Lỗi STT: {e}")
                return {"reply": "", "transcript": ""}

        if not text:
            logger.warning("⚠️ Không có input (text rỗng hoặc STT thất bại).")
            return {"reply": "", "transcript": ""}

        # transcript trả về app = text sau STT normalize (hoặc text gốc nếu không có STT)
        transcript = stt_normalized if stt_normalized is not None else text

        # ── Bước 1: NLU ───────────────────────────────────────────
        nlu_result = predict(text, self.nlu_model, self.sp, self.device, NLU_THRESHOLD)

        # ── Bước 2: Dialog Manager ────────────────────────────────
        dm_output = self.dm.process(nlu_result, raw_text=text)

        # ── Bước 3: NLG hoặc template clarify ────────────────────
        is_clarify = dm_output.startswith('__clarify__')
        if is_clarify:
            response = _clarify_response(dm_output)
        else:
            response = self.nlg.generate(dm_output)

        # ── Bước 3.5: Normalize text trước khi đưa vào TTS ───────
        response_tts = normalize_for_tts(response)

        # ── Bước 4: TTS (blocking) — bỏ qua nếu skip_tts=True ────
        if self.tts is not None and not skip_tts:
            self.tts.speak(response_tts)

        # ── Log chi tiết ──────────────────────────────────────────
        if verbose:
            print(f'\n{"=" * 60}')
            if stt_raw is not None:
                print(f'  🎤 STT raw   : {stt_raw}')
                if stt_raw != stt_normalized:
                    print(f'  🔤 STT norm  : {stt_normalized}')
            print(f'  📝 NLU Input : {text}')
            print(f'{"─" * 60}')
            print(f'  🧠 Intent   : {nlu_result["intent"]}  ({nlu_result["intent_conf"]*100:.1f}%)')
            print(f'  📊 Top-3    :')
            for name, prob in nlu_result['top3']:
                print(f'       {name:<32} {prob*100:5.1f}%')
            if nlu_result['slots']:
                print(f'  🏷  Slots    :')
                for word, lbl, conf in nlu_result['slots']:
                    print(f'       "{word}"  →  {lbl}  ({conf*100:.1f}%)')
            else:
                print(f'  🏷  Slots    : (không có)')
            print(f'{"─" * 60}')
            print(f'  ⚙️  DM Output : {dm_output}')
            print(f'{"─" * 60}')
            if is_clarify:
                print(f'  📢 [CLARIFY] Template response (không qua ViT5)')
            tts_status = "✅ đã phát" if self.tts else "🔇 tắt"
            print(f'  🔊 TTS      : {tts_status}')
            print(f'  🤖 Response : {response}')
            print(f'  📣 TTS text : {response_tts}')
            print(f'  📝 Transcript: {transcript}')
            print(f'{"=" * 60}')

        return {"reply": response, "transcript": transcript}

    # ─────────────────────────────────────────────────────────────

    def reset(self):
        """Reset dialog context."""
        self.dm.reset()
        logger.info("🔄 Dialog context đã reset")

    def show_state(self):
        """In trạng thái hiện tại của dialog."""
        state = self.dm.state
        print('\n📊 Trạng thái Dialog:')
        print(f'  Last device   : {state.last_device}')
        print(f'  Last room     : {state.last_room}')
        print(f'  Last action   : {state.last_action}')
        print(f'  Last intent   : {state.last_intent}')
        print(f'  Last alarm    : {state.last_alarm}')
        print(f'  Last schedule : {state.last_schedule}')
        print(f'  Pending action: {state.pending_action}')
        print(f'  Waiting room  : {state.waiting_room}')
        print(f'\n📟 Trạng thái thiết bị:')
        for k, v in state.device_states.items():
            icon = '🟢' if v == 'on' else ('🔓' if v == 'unlocked' else ('🔒' if v == 'locked' else '⭕'))
            print(f'  {icon} {k:<30}: {v}')


# ─────────────────────────────────────────────
#  INTERACTIVE LOOP
# ─────────────────────────────────────────────

def run_interactive(
    api_base_url  : str  = None,
    enable_stt    : bool = True,
    enable_tts    : bool = True,
    stt_model_dir : str  = None,
    stt_duration  : int  = 3,
):
    """Chạy pipeline ở chế độ tương tác."""
    pipeline = SmartHomePipeline(
        api_base_url  = api_base_url,
        enable_stt    = enable_stt,
        enable_tts    = enable_tts,
        stt_model_dir = stt_model_dir,
        stt_duration  = stt_duration,
    )

    use_stt = (pipeline.stt_model is not None)

    print('\n' + '=' * 60)
    print('  🏠 SMART HOME ASSISTANT — CHẾ ĐỘ TƯƠNG TÁC')
    print('=' * 60)
    print(f'  Đầu vào : {"🎤 Giọng nói (mic)" if use_stt else "⌨️  Bàn phím (text)"}')
    print(f'  Đầu ra  : {"🔊 TTS + text" if pipeline.tts else "💬 Text only"}')
    print('─' * 60)
    print('  Lệnh đặc biệt:')
    print('    reset    → Reset dialog context')
    print('    state    → Xem trạng thái thiết bị & dialog')
    print('    quiet    → Bật/tắt verbose mode')
    if use_stt:
        print('    text     → Chuyển sang chế độ nhập text (1 lượt)')
    print('    quit     → Thoát')
    print('=' * 60)

    verbose = True

    while True:
        try:
            if use_stt:
                cmd = input('\n👤 [Enter=nói / hoặc gõ lệnh]: ').strip()
                cmd_lower = cmd.lower()

                if cmd_lower in ('quit', 'exit', 'q'):
                    print('Tạm biệt!')
                    break
                if cmd_lower == 'reset':
                    pipeline.reset()
                    print('🔄 Đã reset dialog context!')
                    continue
                if cmd_lower == 'state':
                    pipeline.show_state()
                    continue
                if cmd_lower == 'quiet':
                    verbose = not verbose
                    print(f'🔇 Verbose mode: {"ON" if verbose else "OFF"}')
                    continue
                if cmd_lower == 'text':
                    text_input = input('  ✏️  Nhập câu lệnh: ').strip()
                    if text_input:
                        result = pipeline.process(text=text_input, verbose=verbose)
                        if not verbose:
                            print(f'🤖 Bot: {result["reply"]}')
                    continue

                if cmd:
                    result = pipeline.process(text=cmd, verbose=verbose)
                    if not verbose:
                        print(f'🤖 Bot: {result["reply"]}')
                else:
                    try:
                        audio = pipeline._record_audio()
                        result = pipeline.process(audio_array=audio, verbose=verbose)
                        if not verbose and result["reply"]:
                            print(f'🎤 STT : {result["transcript"]}')
                            print(f'🤖 Bot : {result["reply"]}')
                    except Exception as e:
                        logger.error(f"Lỗi thu âm/STT: {e}")

            else:
                text_input = input('\n👤 Bạn: ').strip()
                if not text_input:
                    continue
                text_lower = text_input.lower()

                if text_lower in ('quit', 'exit', 'q'):
                    print('Tạm biệt!')
                    break
                if text_lower == 'reset':
                    pipeline.reset()
                    print('🔄 Đã reset dialog context!')
                    continue
                if text_lower == 'state':
                    pipeline.show_state()
                    continue
                if text_lower == 'quiet':
                    verbose = not verbose
                    print(f'🔇 Verbose mode: {"ON" if verbose else "OFF"}')
                    continue

                result = pipeline.process(text=text_input, verbose=verbose)
                if not verbose:
                    print(f'🤖 Bot: {result["reply"]}')

        except (EOFError, KeyboardInterrupt):
            print('\nTạm biệt!')
            break


# ─────────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────────

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Smart Home Pipeline')
    parser.add_argument('--api-url', type=str, default=None)
    parser.add_argument('--text', type=str, default=None)
    parser.add_argument('--no-stt', action='store_true')
    parser.add_argument('--no-tts', action='store_true')
    parser.add_argument('--stt-model', type=str, default=None)
    parser.add_argument('--duration', type=int, default=3)
    args = parser.parse_args()

    enable_stt = not args.no_stt
    enable_tts = not args.no_tts

    if args.text:
        pipeline = SmartHomePipeline(
            api_base_url  = args.api_url,
            enable_stt    = False,
            enable_tts    = enable_tts,
        )
        pipeline.process(text=args.text, verbose=True)
    else:
        run_interactive(
            api_base_url  = args.api_url,
            enable_stt    = enable_stt,
            enable_tts    = enable_tts,
            stt_model_dir = args.stt_model,
            stt_duration  = args.duration,
        )