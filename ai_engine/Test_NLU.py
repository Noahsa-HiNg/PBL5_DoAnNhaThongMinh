"""
test_nlu.py — Test NLU model (JointBERT INT8 ONNX) qua bàn phím
Đặt file này cùng cấp với thư mục pi5_deploy/

Cấu trúc thư mục:
    test_nlu.py
    pi5_deploy/
        jointbert_int8.onnx
        label_maps.json
        vocab.txt
        bpe.codes
        tokenizer_config.json
        added_tokens.json
        config.json

Cài dependencies:
    pip install onnxruntime transformers
"""

import os, json, sys
import numpy as np

# ══════════════════════════════════════════════════
# CONFIG
# ══════════════════════════════════════════════════

DEPLOY_DIR = os.path.join(os.path.dirname(__file__), 'pi5_deploy')
ONNX_PATH  = os.path.join(DEPLOY_DIR, 'jointbert_int8.onnx')
LABEL_PATH = os.path.join(DEPLOY_DIR, 'label_maps.json')
MAX_LEN    = 64
THRESHOLD  = 0.55        # confidence tối thiểu để nhận intent
TOP_K      = 3           # số intent top hiển thị khi debug


# ══════════════════════════════════════════════════
# LOAD RESOURCES
# ══════════════════════════════════════════════════

def load_resources():
    # Kiểm tra files
    missing = []
    for p in [ONNX_PATH, LABEL_PATH]:
        if not os.path.exists(p):
            missing.append(p)
    if missing:
        print('❌ Thiếu file:')
        for m in missing:
            print(f'   {m}')
        sys.exit(1)

    # Label maps
    with open(LABEL_PATH, 'r', encoding='utf-8') as f:
        lm = json.load(f)
    id2intent = {int(k): v for k, v in lm['id2intent'].items()}
    id2slot   = {int(k): v for k, v in lm['id2slot'].items()}
    slot2id   = lm['slot2id']
    print(f'✅ Label maps: {len(id2intent)} intent | {len(id2slot)} slot')

    # Tokenizer (dùng transformers để load PhoBERT tokenizer từ local)
    from transformers import AutoTokenizer
    tokenizer = AutoTokenizer.from_pretrained(DEPLOY_DIR, use_fast=True)
    print(f'✅ Tokenizer loaded từ {DEPLOY_DIR}')

    # ONNX session
    import onnxruntime as ort
    sess_opts = ort.SessionOptions()
    sess_opts.intra_op_num_threads = 4      # phù hợp Pi 5 (4 core)
    sess_opts.inter_op_num_threads = 1
    sess_opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
    session = ort.InferenceSession(
        ONNX_PATH,
        sess_options=sess_opts,
        providers=['CPUExecutionProvider']
    )
    size_mb = os.path.getsize(ONNX_PATH) / 1024 / 1024
    print(f'✅ ONNX loaded ({size_mb:.1f} MB)')

    return session, tokenizer, id2intent, id2slot, slot2id


# ══════════════════════════════════════════════════
# PREDICT
# ══════════════════════════════════════════════════

def predict(text, session, tokenizer, id2intent, id2slot):
    words = text.strip().split()
    if not words:
        return None

    # Tokenize word-by-word, giữ nguyên logic lúc train
    all_input_ids    = [tokenizer.cls_token_id]
    word_token_spans = []

    for word in words:
        token_ids = tokenizer.encode(word, add_special_tokens=False)
        if not token_ids:
            token_ids = [tokenizer.unk_token_id]
        start = len(all_input_ids)
        all_input_ids.extend(token_ids)
        word_token_spans.append((start, len(all_input_ids)))

    all_input_ids.append(tokenizer.sep_token_id)

    # Truncate
    if len(all_input_ids) > MAX_LEN:
        all_input_ids    = all_input_ids[:MAX_LEN - 1] + [tokenizer.sep_token_id]
        word_token_spans = [(s, min(e, MAX_LEN - 1)) for s, e in word_token_spans]

    # Padding
    pad_len        = MAX_LEN - len(all_input_ids)
    attention_mask = [1] * len(all_input_ids) + [0] * pad_len
    all_input_ids  = all_input_ids + [tokenizer.pad_token_id] * pad_len

    ids_np  = np.array([all_input_ids],  dtype=np.int64)
    mask_np = np.array([attention_mask], dtype=np.int64)

    # Inference
    intent_logits, slot_logits = session.run(
        None,
        {'input_ids': ids_np, 'attention_mask': mask_np}
    )

    # Intent
    probs       = _softmax(intent_logits[0])
    intent_id   = int(probs.argmax())
    confidence  = float(probs[intent_id])
    intent_name = id2intent[intent_id]
    top_k       = [(id2intent[i], round(float(probs[i]), 4))
                   for i in probs.argsort()[::-1][:TOP_K]]

    # Slot → entities (BIO decode)
    slot_preds = slot_logits[0].argmax(axis=-1)   # [MAX_LEN]
    entities   = []
    cur_type   = None
    cur_words  = []

    for word, (span_start, _) in zip(words, word_token_spans):
        if span_start >= MAX_LEN:
            break
        label = id2slot[int(slot_preds[span_start])]

        if label.startswith('B-'):
            if cur_words and cur_type:
                entities.append({'entity': cur_type, 'value': ' '.join(cur_words)})
            cur_type  = label[2:]
            cur_words = [word]

        elif label.startswith('I-') and cur_type == label[2:]:
            cur_words.append(word)

        else:
            if cur_words and cur_type:
                entities.append({'entity': cur_type, 'value': ' '.join(cur_words)})
            cur_type  = None
            cur_words = []

    if cur_words and cur_type:
        entities.append({'entity': cur_type, 'value': ' '.join(cur_words)})

    return {
        'intent':     intent_name,
        'confidence': round(confidence, 4),
        'entities':   entities,
        'top_k':      top_k,
    }


def _softmax(x):
    e = np.exp(x - x.max())
    return e / e.sum()


# ══════════════════════════════════════════════════
# DISPLAY
# ══════════════════════════════════════════════════

ENTITY_COLORS = {
    'action_on':  '\033[92m',   # xanh lá
    'action_off': '\033[91m',   # đỏ
    'action_adj': '\033[93m',   # vàng
    'action_check':'\033[96m',  # cyan
    'device':     '\033[94m',   # xanh dương
    'room':       '\033[95m',   # tím
    'value':      '\033[93m',   # vàng
    'sensor':     '\033[96m',   # cyan
}
RESET = '\033[0m'
BOLD  = '\033[1m'
DIM   = '\033[2m'

def _bar(prob, width=20):
    filled = int(prob * width)
    return '█' * filled + '░' * (width - filled)

def display_result(result, debug=False):
    intent     = result['intent']
    confidence = result['confidence']
    entities   = result['entities']
    top_k      = result['top_k']

    # Confidence color
    if confidence >= 0.85:
        conf_color = '\033[92m'
    elif confidence >= THRESHOLD:
        conf_color = '\033[93m'
    else:
        conf_color = '\033[91m'

    print()
    print(f'  {BOLD}Intent:{RESET}  {conf_color}{intent}{RESET}')
    print(f'  {BOLD}Conf  :{RESET}  {conf_color}{_bar(confidence)} {confidence:.2%}{RESET}')

    if entities:
        print(f'  {BOLD}Entities:{RESET}')
        for e in entities:
            c   = ENTITY_COLORS.get(e['entity'], '')
            tag = f'{c}[{e["entity"]}]{RESET}'
            print(f'    {tag}  "{e["value"]}"')
    else:
        print(f'  {DIM}Entities: (none){RESET}')

    if debug:
        print(f'\n  {DIM}Top-{TOP_K}:{RESET}')
        for name, prob in top_k:
            bar  = _bar(prob, width=15)
            mark = ' ←' if name == intent else ''
            print(f'    {DIM}{bar} {prob:.4f}  {name}{mark}{RESET}')

    if confidence < THRESHOLD:
        print(f'\n  \033[91m⚠ Confidence thấp ({confidence:.2%} < {THRESHOLD:.0%}) — kết quả có thể không chính xác\033[0m')


# ══════════════════════════════════════════════════
# MAIN LOOP
# ══════════════════════════════════════════════════

BANNER = """
╔══════════════════════════════════════════════════════╗
║        SMART HOME NLU — TEST TERMINAL                ║
║        Model: JointBERT-PhoBERT INT8 ONNX            ║
╠══════════════════════════════════════════════════════╣
║  Nhập câu tiếng Việt → Enter để phân tích            ║
║  Lệnh:  debug  →  bật/tắt chi tiết top-K            ║
║         bench  →  đo tốc độ inference (100 lần)      ║
║         quit   →  thoát                              ║
╚══════════════════════════════════════════════════════╝
"""

def benchmark(session, tokenizer, id2intent, id2slot):
    import time
    sample = 'bật đèn phòng khách cho tôi'
    times  = []
    print(f'  Benchmarking 100 lần với: "{sample}"')
    for _ in range(100):
        t0 = time.perf_counter()
        predict(sample, session, tokenizer, id2intent, id2slot)
        times.append((time.perf_counter() - t0) * 1000)
    arr = np.array(times)
    print(f'  Avg  : {arr.mean():.1f} ms')
    print(f'  Min  : {arr.min():.1f} ms')
    print(f'  Max  : {arr.max():.1f} ms')
    print(f'  P95  : {np.percentile(arr, 95):.1f} ms')


def main():
    print(BANNER)
    print('  Đang load model...')

    session, tokenizer, id2intent, id2slot, _ = load_resources()

    print(f'\n  Model sẵn sàng! Bắt đầu nhập câu:\n')
    print('─' * 56)

    debug_mode = False

    while True:
        try:
            text = input('\n🎤  ').strip()
        except (EOFError, KeyboardInterrupt):
            print('\n\nThoát. Bye! 👋')
            break

        if not text:
            continue

        cmd = text.lower()

        if cmd in ('quit', 'exit', 'q'):
            print('\nThoát. Bye! 👋')
            break

        if cmd == 'debug':
            debug_mode = not debug_mode
            state = 'BẬT' if debug_mode else 'TẮT'
            print(f'  🔍 Debug mode: {state}')
            continue

        if cmd == 'bench':
            benchmark(session, tokenizer, id2intent, id2slot)
            continue

        # Inference
        result = predict(text, session, tokenizer, id2intent, id2slot)
        if result is None:
            print('  (câu rỗng, bỏ qua)')
            continue

        display_result(result, debug=debug_mode)


if __name__ == '__main__':
    main()