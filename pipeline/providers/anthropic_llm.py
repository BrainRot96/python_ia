# pipeline/providers/anthropic_llm.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, List
import anthropic

@dataclass
class AnthropicLLM:
    model: str = "claude-3-5-sonnet-20240620"

    def __post_init__(self):
        # La lib lit ANTHROPIC_API_KEY depuis l'env
        self.client = anthropic.Anthropic()

    def generate(
        self,
        prompt: str,
        *,
        max_tokens: int = 300,
        temperature: float = 0.2,
        system: str | None = "Tu es un assistant utile et concis. Réponds en français."
    ) -> Dict[str, Any]:
        # API Anthropic “messages”
        messages = [{"role": "user", "content": prompt}]
        resp = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system or "",
            messages=messages,
        )
        # Le contenu est une liste de blocs (type "text")
        parts = resp.content or []
        text = "".join(getattr(p, "text", "") for p in parts).strip()

        # Anthropic ne renvoie pas toujours un usage complet ; on normalise
        usage_dict = {}
        if getattr(resp, "usage", None):
            usage_dict = {
                "input_tokens": getattr(resp.usage, "input_tokens", None),
                "output_tokens": getattr(resp.usage, "output_tokens", None),
                "total_tokens": (
                    (getattr(resp.usage, "input_tokens", 0) or 0) +
                    (getattr(resp.usage, "output_tokens", 0) or 0)
                ),
            }

        return {"text": text, "usage": usage_dict}
    