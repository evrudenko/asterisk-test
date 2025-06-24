import asyncio

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer


class LLMService:

    def __init__(self, model_name="sberbank-ai/rugpt3small_based_on_gpt2", device=None):
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForCausalLM.from_pretrained(model_name)
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.model.to(self.device)

    def generate(self, instruction, max_new_tokens=100, temperature=0.7, top_p=0.9):
        # Подготовка входных данных
        inputs = self.tokenizer(instruction, return_tensors="pt").to(self.device)

        # Генерация текста
        outputs = self.model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            temperature=temperature,
            top_p=top_p,
            do_sample=True,
            repetition_penalty=1.2,
            pad_token_id=self.tokenizer.eos_token_id,
            eos_token_id=self.tokenizer.eos_token_id,
        )

        # Декодирование
        return self.tokenizer.decode(outputs[0], skip_special_tokens=True)

    async def generate_async(
        self, instruction, max_new_tokens=100, temperature=0.7, top_p=0.9
    ) -> bytes:
        return await asyncio.to_thread(
            self.generate, instruction, max_new_tokens, temperature, top_p
        )
