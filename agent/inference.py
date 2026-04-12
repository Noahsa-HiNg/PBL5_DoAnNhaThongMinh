
import os, json, math, torch
import torch.nn as nn
import sentencepiece as spm

# ─────────────────────────────────────────────
#  PATHS  (chỉnh nếu đặt folder khác)
# ─────────────────────────────────────────────
BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
TOKENIZER   = os.path.join(BASE_DIR, "tokenizer", "vi_smarthome_bpe.model")
CHECKPOINT  = os.path.join(BASE_DIR, "model", "micro_bert_best.pt")


# ─────────────────────────────────────────────
#  LABELS  (phải khớp 100% với lúc train)
# ─────────────────────────────────────────────
INTENT_LABELS = [
    'control_device', 'query_status', 'query_sensor',
    'query_time', 'query_weather',
    'schedule_set', 'schedule_cancel',
    'alarm_set', 'alarm_cancel',
    'context_arrive', 'context_leave', 'context_sleep', 'context_wake',
    'context_hot', 'context_cold', 'context_stuffy',
    'confirm_yes', 'confirm_no',
    'chitchat', 'unsupported',
]

SLOT_LABELS_RAW = [
    'action_adj-adj_down', 'action_adj-adj_up',
    'action_check-check',
    'action_lock-lock', 'action_lock-unlock',
    'action_off-off', 'action_off-off_all',
    'action_on-on', 'action_on-on_all',
    'device-all', 'device-door_lock', 'device-fan',
    'device-light', 'device-ventilation_fan',
    'room-all', 'room-bedroom', 'room-kitchen',
    'room-living_room', 'room-yard',
    'sensor-all', 'sensor-co2', 'sensor-humidity', 'sensor-temperature',
    'signal_arrive', 'signal_cold', 'signal_hot',
    'signal_leave', 'signal_sleep', 'signal_stuffy', 'signal_wake',
    'time_absolute', 'time_delay',
    'value',
]

SLOT_LABELS = ['O']
for label in SLOT_LABELS_RAW:
    SLOT_LABELS.append(f'B-{label}')
    SLOT_LABELS.append(f'I-{label}')

IGNORE_IDX  = -100
MAX_LEN     = 64
NUM_INTENTS = len(INTENT_LABELS)   # 20
NUM_SLOTS   = len(SLOT_LABELS)     # 67

intent2id = {l: i for i, l in enumerate(INTENT_LABELS)}
slot2id   = {l: i for i, l in enumerate(SLOT_LABELS)}
id2intent = {i: l for l, i in intent2id.items()}
id2slot   = {i: l for l, i in slot2id.items()}


# ─────────────────────────────────────────────
#  MODEL ARCHITECTURE  (copy nguyên từ notebook)
# ─────────────────────────────────────────────
class MultiHeadAttention(nn.Module):
    def __init__(self, hidden, n_heads, dropout=0.1):
        super().__init__()
        assert hidden % n_heads == 0
        self.d_k     = hidden // n_heads
        self.n_heads = n_heads
        self.qkv     = nn.Linear(hidden, hidden * 3)
        self.out     = nn.Linear(hidden, hidden)
        self.dropout = nn.Dropout(dropout)

    def forward(self, x, mask=None):
        B, T, C = x.shape
        qkv = self.qkv(x).reshape(B, T, 3, self.n_heads, self.d_k)
        qkv = qkv.permute(2, 0, 3, 1, 4)
        q, k, v = qkv[0], qkv[1], qkv[2]
        scores = (q @ k.transpose(-2, -1)) / math.sqrt(self.d_k)
        if mask is not None:
            scores = scores.masked_fill(
                mask.unsqueeze(1).unsqueeze(2) == 0, float('-inf')
            )
        attn = self.dropout(torch.softmax(scores, dim=-1))
        out  = (attn @ v).transpose(1, 2).reshape(B, T, C)
        return self.out(out)


class FeedForward(nn.Module):
    def __init__(self, hidden, ffn_dim, dropout=0.1):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(hidden, ffn_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(ffn_dim, hidden),
            nn.Dropout(dropout),
        )
    def forward(self, x): return self.net(x)


class TransformerBlock(nn.Module):
    def __init__(self, hidden, n_heads, ffn_dim, dropout=0.1):
        super().__init__()
        self.attn = MultiHeadAttention(hidden, n_heads, dropout)
        self.ff   = FeedForward(hidden, ffn_dim, dropout)
        self.ln1  = nn.LayerNorm(hidden)
        self.ln2  = nn.LayerNorm(hidden)

    def forward(self, x, mask=None):
        x = x + self.attn(self.ln1(x), mask)
        x = x + self.ff(self.ln2(x))
        return x


class MicroBERT_NLU(nn.Module):
    def __init__(self, vocab_size, hidden=128, n_layers=3, n_heads=4,
                 ffn_dim=512, max_len=64,
                 num_intents=NUM_INTENTS, num_slots=NUM_SLOTS,
                 dropout=0.1, pad_id=0):
        super().__init__()
        self.tok_emb  = nn.Embedding(vocab_size, hidden, padding_idx=pad_id)
        self.pos_emb  = nn.Embedding(max_len, hidden)
        self.emb_drop = nn.Dropout(dropout)
        self.emb_norm = nn.LayerNorm(hidden)
        self.layers   = nn.ModuleList([
            TransformerBlock(hidden, n_heads, ffn_dim, dropout)
            for _ in range(n_layers)
        ])
        self.intent_head = nn.Linear(hidden, num_intents)
        self.slot_head   = nn.Linear(hidden, num_slots)

    def forward(self, input_ids, attention_mask):
        B, T = input_ids.shape
        pos  = torch.arange(T, device=input_ids.device).unsqueeze(0)
        x    = self.tok_emb(input_ids) + self.pos_emb(pos)
        x    = self.emb_norm(self.emb_drop(x))
        for layer in self.layers:
            x = layer(x, attention_mask)
        intent_logits = self.intent_head(x[:, 0, :])
        slot_logits   = self.slot_head(x)
        return intent_logits, slot_logits


# ─────────────────────────────────────────────
#  ENCODE  (copy nguyên từ notebook)
# ─────────────────────────────────────────────
def encode_text(text, sp):
    """Encode raw text (không cần label) để inference."""
    sample = {'text': text, 'intent': 'unsupported', 'entities': []}
    char_slot = ['O'] * len(text)

    token_ids = [sp.bos_id()]
    slot_ids  = [IGNORE_IDX]

    i = 0
    for word in text.split():
        while i < len(text) and text[i] == ' ':
            i += 1
        word_start = i
        pieces = sp.encode_as_ids(word)
        slot_for_word = char_slot[word_start] if word_start < len(char_slot) else 'O'

        token_ids.append(pieces[0])
        slot_ids.append(slot2id.get(slot_for_word, slot2id['O']))

        for p in pieces[1:]:
            token_ids.append(p)
            slot_ids.append(IGNORE_IDX)
        i += len(word)

    token_ids.append(sp.eos_id())
    slot_ids.append(IGNORE_IDX)

    token_ids = token_ids[:MAX_LEN]
    pad_len   = MAX_LEN - len(token_ids)
    attention_mask = [1] * len(token_ids) + [0] * pad_len
    token_ids     += [sp.pad_id()] * pad_len

    return {
        'input_ids':      torch.tensor(token_ids,      dtype=torch.long),
        'attention_mask': torch.tensor(attention_mask, dtype=torch.long),
    }


# ─────────────────────────────────────────────
#  PREDICT
# ─────────────────────────────────────────────
def predict(text: str, model, sp, device, threshold=0.5):
    model.eval()
    enc = encode_text(text, sp)

    input_ids      = enc['input_ids'].unsqueeze(0).to(device)
    attention_mask = enc['attention_mask'].unsqueeze(0).to(device)

    with torch.no_grad():
        intent_logits, slot_logits = model(input_ids, attention_mask)

    # Intent
    intent_probs = torch.softmax(intent_logits, dim=-1)[0]
    intent_id    = intent_probs.argmax().item()
    intent_name  = id2intent[intent_id]
    intent_conf  = intent_probs[intent_id].item()
    top3_vals, top3_ids = intent_probs.topk(3)
    top3 = [(id2intent[i.item()], v.item()) for i, v in zip(top3_ids, top3_vals)]

    # Slot
    slot_probs    = torch.softmax(slot_logits, dim=-1)[0]
    slot_ids_pred = slot_probs.argmax(dim=-1).tolist()

    words, word_slots, token_pos = text.split(), [], 1
    for word in words:
        pieces = sp.encode_as_ids(word)
        pos    = token_pos
        if pos < MAX_LEN:
            s_id   = slot_ids_pred[pos]
            s_conf = slot_probs[pos, s_id].item()
        else:
            s_id, s_conf = 0, 0.0
        word_slots.append((word, id2slot.get(s_id, 'O'), s_conf))
        token_pos += len(pieces)

    detected_slots = [
        (w, lbl, c) for w, lbl, c in word_slots
        if lbl != 'O' and c >= threshold
    ]

    return {
        'text':           text,
        'intent':         intent_name,
        'intent_conf':    intent_conf,
        'top3':           top3,
        'slots':          detected_slots,    # [(word, label, conf), ...]
        'all_word_slots': word_slots,
    }


def print_result(result, threshold=0.5):
    print(f"\n{'='*55}")
    print(f"  Input  : {result['text']}")
    print(f"{'='*55}")
    print(f"  Intent : {result['intent']:<25} {result['intent_conf']*100:5.1f}%")
    print(f"  Top-3  :")
    for name, prob in result['top3']:
        print(f"    {name:<32} {prob*100:5.1f}%")
    if result['slots']:
        print(f"  Slots  :")
        for word, label, conf in result['slots']:
            print(f'    "{word}"  →  {label}  ({conf*100:.1f}%)')
    else:
        print(f"  Slots  : (không có slot nào >= {threshold*100:.0f}%)")
    print('='*55)


# ─────────────────────────────────────────────
#  LOAD MODEL
# ─────────────────────────────────────────────
def load_model(device=None):
    if device is None:
        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

    print(f"🔄 Đang load tokenizer từ: {TOKENIZER}")
    sp = spm.SentencePieceProcessor()
    sp.load(TOKENIZER)
    print(f"✅ Tokenizer loaded | vocab_size: {sp.get_piece_size()}")

    print(f"🔄 Đang load checkpoint từ: {CHECKPOINT}")
    ckpt = torch.load(CHECKPOINT, map_location=device)

    # Nếu checkpoint có lưu intent2id/slot2id thì dùng từ đó (an toàn hơn)
    if 'intent2id' in ckpt:
        _i2id = ckpt['intent2id']
        _s2id = ckpt['slot2id']
        print(f"   Dùng label mapping từ checkpoint ({len(_i2id)} intents, {len(_s2id)} slots)")

    model = MicroBERT_NLU(
        vocab_size = sp.get_piece_size(),
        pad_id     = sp.pad_id(),
    ).to(device)
    model.load_state_dict(ckpt['model_state'])
    model.eval()

    epoch = ckpt.get('epoch', '?')
    print(f"✅ Model loaded | trained epoch: {epoch} | device: {device}")
    return model, sp, device


# ─────────────────────────────────────────────
#  MAIN — chạy interactive loop
# ─────────────────────────────────────────────
if __name__ == '__main__':
    model, sp, device = load_model()

    print("\n🏠 Smart Home NLU — Interactive Mode")
    print("   Gõ 'quit' để thoát\n")

    while True:
        try:
            text = input("Nhập câu lệnh: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye!")
            break

        if text.lower() in ('quit', 'exit', 'q', ''):
            break

        result = predict(text, model, sp, device)
        print_result(result)