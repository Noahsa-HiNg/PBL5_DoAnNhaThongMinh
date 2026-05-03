"""
pipeline.py — Smart Home Pipeline hoàn chỉnh
NLU (micro-BERT) → Dialog Manager v9 → API → NLG (ViT5) → Normalize → TTS (MeloTTS)

Usage:
    python pipeline.py
    python pipeline.py --no-tts          # tắt TTS
    python pipeline.py --text "bật đèn"  # chạy 1 câu rồi thoát
"""

import logging
import torch

# ── Cấu hình logging ───────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
)
logger = logging.getLogger(__name__)

# ── Import các thành phần ──────────────────────────────────────────
from inference      import load_model, predict
from api_client     import SmartHomeAPIClient
from dialog_manager import SmartHomeDialogManager
from vit5_generator import ViT5Generator
from tts_speaker    import TTSSpeaker
from tts_normalizer import normalize_for_tts       # ← THÊM
from config         import NLU_THRESHOLD


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
    Pipeline hoàn chỉnh: Text → NLU → DM → API → NLG → Normalize → TTS

    Args:
        api_base_url: URL API server (mặc định localhost:5000)
        enable_tts:   Bật/tắt TTS (mặc định True)
    """

    def __init__(self, api_base_url: str = None, enable_tts: bool = True):
        logger.info("=" * 55)
        logger.info("  🏠 Khởi động Smart Home Pipeline")
        logger.info("=" * 55)

        # 1. Load NLU
        logger.info("📦 [1/4] Loading micro-BERT NLU...")
        self.nlu_model, self.sp, self.device = load_model()

        # 2. Setup API + Dialog Manager
        logger.info("🔌 [2/4] Khởi tạo API Client + Dialog Manager...")
        kwargs   = {'base_url': api_base_url} if api_base_url else {}
        self.api = SmartHomeAPIClient(**kwargs)
        self.dm  = SmartHomeDialogManager(api_client=self.api)

        # 3. Load NLG
        logger.info("📦 [3/4] Loading ViT5 NLG...")
        self.nlg = ViT5Generator(device=self.device)

        # 4. Load TTS
        self.tts: TTSSpeaker | None = None
        if enable_tts:
            logger.info("🔊 [4/4] Loading MeloTTS...")
            try:
                self.tts = TTSSpeaker(device=str(self.device))
            except Exception as e:
                # TTS lỗi không làm sập pipeline — chỉ warn
                logger.warning(f"⚠️ TTS không khởi động được, bỏ qua: {e}")
        else:
            logger.info("🔇 [4/4] TTS bị tắt (--no-tts)")

        logger.info("✅ Pipeline sẵn sàng!\n")

    # ─────────────────────────────────────────────
    def process(self, text: str, verbose: bool = True) -> str:
        """
        Xử lý một câu lệnh đầu vào.

        Args:
            text:    Câu lệnh tiếng Việt của user
            verbose: In chi tiết từng bước

        Returns:
            Câu phản hồi tiếng Việt (text gốc từ ViT5, chưa normalize)
        """
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
        # response_tts: bản đã chuẩn hóa (°C→"độ C", %→"phần trăm", v.v.)
        # response    : giữ nguyên text gốc để log & return cho caller
        response_tts = normalize_for_tts(response)

        # ── Bước 4: TTS (blocking) ────────────────────────────────
        if self.tts is not None:
            self.tts.speak(response_tts)

        # ── Log chi tiết ──────────────────────────────────────────
        if verbose:
            print(f'\n{"=" * 60}')
            print(f'  📝 Input    : {text}')
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
            print(f'  📣 TTS text : {response_tts}')   # ← log thêm bản đã normalize
            print(f'{"=" * 60}')

        return response

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

def run_interactive(api_base_url: str = None, enable_tts: bool = True):
    """Chạy pipeline ở chế độ tương tác."""
    pipeline = SmartHomePipeline(api_base_url=api_base_url, enable_tts=enable_tts)

    print('\n' + '=' * 60)
    print('  🏠 SMART HOME ASSISTANT — CHẾ ĐỘ TƯƠNG TÁC')
    print('=' * 60)
    print('  Lệnh đặc biệt:')
    print('    reset    → Reset dialog context')
    print('    state    → Xem trạng thái thiết bị & dialog')
    print('    quiet    → Bật/tắt verbose mode')
    print('    quit     → Thoát')
    print('=' * 60)

    verbose = True

    while True:
        try:
            text = input('\n👤 Bạn: ').strip()
        except (EOFError, KeyboardInterrupt):
            print('\nTạm biệt!')
            break

        if not text:
            continue

        text_lower = text.lower()

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

        response = pipeline.process(text, verbose=verbose)
        if not verbose:
            print(f'🤖 Bot: {response}')


# ─────────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────────

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Smart Home Pipeline')
    parser.add_argument(
        '--api-url',
        type=str,
        default=None,
        help='Base URL của API server (mặc định: http://localhost:5000)',
    )
    parser.add_argument(
        '--text',
        type=str,
        default=None,
        help='Chạy một câu lệnh rồi thoát (không cần interactive)',
    )
    parser.add_argument(
        '--no-tts',
        action='store_true',
        help='Tắt TTS (chỉ in text ra terminal)',
    )
    args = parser.parse_args()

    enable_tts = not args.no_tts

    if args.text:
        pipeline = SmartHomePipeline(api_base_url=args.api_url, enable_tts=enable_tts)
        pipeline.process(args.text, verbose=True)
    else:
        run_interactive(api_base_url=args.api_url, enable_tts=enable_tts)