# pipeline/providers/ollama_llm.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any
import requests
import time

class LLMProviderError(Exception):
    pass

@dataclass
class OllamaLLM:
    model: str = "mistral"
    endpoint: str = "http://localhost:11434/api/generate"
    timeout_s: int = 30
    max_retries: int = 2
    backoff_s: float = 0.8  # petit backoff progressif

    def generate(
        self,
        prompt: str,
        *,
        max_tokens: int = 300,
        temperature: float = 0.2,
        context: str = "",
    ) -> Dict[str, Any]:
        full_prompt = f"Contexte:\n{context}\n\nQuestion:\n{prompt}" if context else prompt
        payload = {
            "model": self.model,
            "prompt": full_prompt,
            "options": {
                "temperature": float(temperature),
                "num_predict": int(max_tokens),
            },
            "stream": False,
        }

        last_err = None
        for attempt in range(self.max_retries + 1):
            try:
                resp = requests.post(self.endpoint, json=payload, timeout=self.timeout_s)
                resp.raise_for_status()
                data = resp.json()
                text = data.get("response", "") or data.get("message", "")
                usage = {
                    "prompt_tokens": data.get("prompt_eval_count"),
                    "completion_tokens": data.get("eval_count"),
                    "total_tokens": (data.get("prompt_eval_count") or 0) + (data.get("eval_count") or 0),
                }
                return {"text": text, "usage": usage}
            except Exception as e:
                last_err = e
                if attempt < self.max_retries:
                    time.sleep(self.backoff_s * (attempt + 1))
                else:
                    raise LLMProviderError(f"Ollama error after retries: {e}") from e
                