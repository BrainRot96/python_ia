# pipeline/providers/openai_llm.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, List
import os

from openai import OpenAI

@dataclass
class OpenAILLM:
    model: str = "gpt-4o-mini"

    def __post_init__(self):
        # La lib OpenAI lit OPENAI_API_KEY depuis l'env automatiquement.
        self.client = OpenAI()

    def generate(
        self,
        prompt: str,
        *,
        max_tokens: int = 300,
        temperature: float = 0.2,
        system: str | None = "Tu es un assistant utile et concis. Réponds en français."
    ) -> Dict[str, Any]:
        messages: List[Dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        resp = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        choice = resp.choices[0].message
        text = (choice.content or "").strip()

        usage = getattr(resp, "usage", None)
        usage_dict = {
            "prompt_tokens": getattr(usage, "prompt_tokens", None),
            "completion_tokens": getattr(usage, "completion_tokens", None),
            "total_tokens": getattr(usage, "total_tokens", None),
        } if usage else {}

        return {"text": text, "usage": usage_dict}
    