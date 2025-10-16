# pipeline/providers/ollama_llm.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, Generator, Optional
import requests
import json

@dataclass
class OllamaLLM:
    model: str = "mistral"
    endpoint: str = "http://localhost:11434/api/generate"

    def _build_payload(self, prompt: str, max_tokens: int, temperature: float, context: str) -> Dict[str, Any]:
        full_prompt = f"Contexte:\n{context}\n\nQuestion:\n{prompt}" if context else prompt
        return {
            "model": self.model,
            "prompt": full_prompt,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }

    def generate(self, prompt: str, *, max_tokens: int = 300, temperature: float = 0.2, context: str = "") -> Dict[str, Any]:
        payload = self._build_payload(prompt, max_tokens, temperature, context)
        payload["stream"] = False
        r = requests.post(self.endpoint, json=payload, timeout=60)
        r.raise_for_status()
        data = r.json()
        text = data.get("response", "") or data.get("text", "")
        usage = {
            "prompt_tokens": data.get("prompt_eval_count"),
            "completion_tokens": data.get("eval_count"),
            "total_tokens": (
                (data.get("prompt_eval_count") or 0) + (data.get("eval_count") or 0)
            ),
        }
        return {"text": text, "usage": usage}

    def generate_stream(
        self, prompt: str, *, max_tokens: int = 300, temperature: float = 0.2, context: str = ""
    ) -> Generator[str, None, Dict[str, Any]]:
        """
        Génère la réponse en streaming. Yield des fragments de texte.
        À la fin, retourne un dict usage via `return`.
        """
        payload = self._build_payload(prompt, max_tokens, temperature, context)
        payload["stream"] = True

        with requests.post(self.endpoint, json=payload, timeout=300, stream=True) as r:
            r.raise_for_status()
            total_text = []
            prompt_tokens = completion_tokens = 0
            for line in r.iter_lines(decode_unicode=True):
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except Exception:
                    continue
                if "response" in obj:  # fragment de texte
                    chunk = obj["response"] or ""
                    if chunk:
                        total_text.append(chunk)
                        yield chunk
                if obj.get("done"):
                    prompt_tokens = obj.get("prompt_eval_count") or 0
                    completion_tokens = obj.get("eval_count") or 0
                    break

        usage = {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
        }
        return usage
    