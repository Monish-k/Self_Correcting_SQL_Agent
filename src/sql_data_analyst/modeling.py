from __future__ import annotations

from typing import Dict, List, Optional

import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

from .config import AppConfig


class SQLModel:
    def __init__(self, config: AppConfig):
        self.config = config
        self.tokenizer = None
        self.model = None

    def ensure_loaded(self) -> None:
        if self.model is not None and self.tokenizer is not None:
            return

        self.config.validate()
        self.tokenizer = AutoTokenizer.from_pretrained(
            self.config.base_model_id, token=self.config.hf_token, use_fast=True
        )
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
        self.tokenizer.padding_side = "right"

        use_cuda = torch.cuda.is_available()
        if use_cuda:
            bnb_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=torch.float16,
                bnb_4bit_use_double_quant=True,
            )
            base_model = AutoModelForCausalLM.from_pretrained(
                self.config.base_model_id,
                quantization_config=bnb_config,
                torch_dtype=torch.float16,
                device_map="auto",
                token=self.config.hf_token,
            )
        else:
            base_model = AutoModelForCausalLM.from_pretrained(
                self.config.base_model_id,
                torch_dtype=torch.bfloat16,
                low_cpu_mem_usage=True,
                token=self.config.hf_token,
            )
            base_model.to("cpu")

        self.model = PeftModel.from_pretrained(base_model, self.config.adapter_source, token=self.config.hf_token)
        self.model.eval()

    def generate_completion(self, messages: List[Dict[str, str]], max_new_tokens: Optional[int] = None) -> str:
        self.ensure_loaded()

        prompt_text = self.tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
        )

        inputs = self.tokenizer(
            prompt_text,
            return_tensors="pt",
            truncation=True,
            max_length=self.config.max_input_tokens,
        )

        if torch.cuda.is_available():
            inputs = inputs.to(self.model.device)

        with torch.inference_mode():
            output_ids = self.model.generate(
                **inputs,
                max_new_tokens=max_new_tokens or self.config.sql_max_new_tokens,
                do_sample=False,
                num_beams=1,
                use_cache=True,
                pad_token_id=self.tokenizer.pad_token_id,
                eos_token_id=self.tokenizer.eos_token_id,
            )

        generated = output_ids[0][inputs["input_ids"].shape[1] :]
        return self.tokenizer.decode(generated, skip_special_tokens=True).strip()
