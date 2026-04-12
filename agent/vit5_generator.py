"""
vit5_generator.py — Wrapper cho ViT5 NLG model
Ported từ vit5-shmv2.ipynb (Cell 5, 8) và SmartHome_DialogManager_v9.ipynb (Cell 8)
"""

import torch
import logging
from pathlib import Path
from transformers import T5ForConditionalGeneration, T5Tokenizer

from config import NLG_MODEL_DIR, NLG_MAX_INPUT, NLG_MAX_NEW_TOK, NLG_NUM_BEAMS

logger = logging.getLogger(__name__)


class ViT5Generator:
    """
    Wrapper ViT5 sinh câu phản hồi tiếng Việt từ DM output string.

    Usage:
        gen = ViT5Generator()
        response = gen.generate("RESULT:light_bedroom:on | control_device | ...")
    """

    def __init__(
        self,
        model_dir:    str = NLG_MODEL_DIR,
        max_input:    int = NLG_MAX_INPUT,
        max_new_tok:  int = NLG_MAX_NEW_TOK,
        num_beams:    int = NLG_NUM_BEAMS,
        device:       torch.device = None,
    ):
        self.max_input   = max_input
        self.max_new_tok = max_new_tok
        self.num_beams   = num_beams

        if device is None:
            self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        else:
            self.device = device

        # Fix Windows backslash path — transformers chỉ nhận forward slash
        model_dir = str(Path(model_dir).resolve()).replace('\\', '/')

        logger.info(f"🔄 Loading ViT5 tokenizer từ: {model_dir}")
        # legacy=True để tránh warning với sentencepiece tokenizer
        self.tokenizer = T5Tokenizer.from_pretrained(model_dir, legacy=True)
        logger.info("✅ ViT5 tokenizer loaded")

        logger.info(f"🔄 Loading ViT5 model từ: {model_dir} (có thể mất 30-60s)...")
        self.model = T5ForConditionalGeneration.from_pretrained(model_dir)
        self.model = self.model.to(self.device)
        self.model.eval()
        logger.info(f"✅ ViT5 model loaded | device: {self.device}")

    def generate(self, dm_output: str) -> str:
        """
        Nhận structured string từ Dialog Manager → sinh câu phản hồi tiếng Việt.

        Args:
            dm_output: Chuỗi DM output, ví dụ:
                       "RESULT:light_bedroom:on | control_device | action_on-on |
                        device-light | room-bedroom | action_label=bật"

        Returns:
            Câu phản hồi tiếng Việt, ví dụ: "Dạ em bật đèn phòng ngủ rồi ạ."
        """
        enc = self.tokenizer(
            dm_output,
            max_length=self.max_input,
            truncation=True,
            return_tensors='pt',
        )
        input_ids      = enc['input_ids'].to(self.device)
        attention_mask = enc['attention_mask'].to(self.device)

        with torch.no_grad():
            out_ids = self.model.generate(
                input_ids=input_ids,
                attention_mask=attention_mask,
                max_new_tokens=self.max_new_tok,
                num_beams=self.num_beams,
                early_stopping=True,
            )

        response = self.tokenizer.decode(out_ids[0], skip_special_tokens=True)
        return response

    def batch_generate(self, dm_outputs: list) -> list:
        """
        Sinh nhiều câu phản hồi cùng lúc (batch inference).
        Phù hợp khi cần evaluate hoặc test số lượng lớn.

        Args:
            dm_outputs: Danh sách DM output strings

        Returns:
            Danh sách câu phản hồi
        """
        if not dm_outputs:
            return []

        enc = self.tokenizer(
            dm_outputs,
            max_length=self.max_input,
            padding=True,
            truncation=True,
            return_tensors='pt',
        )
        input_ids      = enc['input_ids'].to(self.device)
        attention_mask = enc['attention_mask'].to(self.device)

        with torch.no_grad():
            out_ids = self.model.generate(
                input_ids=input_ids,
                attention_mask=attention_mask,
                max_new_tokens=self.max_new_tok,
                num_beams=self.num_beams,
                early_stopping=True,
            )

        return [
            self.tokenizer.decode(ids, skip_special_tokens=True)
            for ids in out_ids
        ]