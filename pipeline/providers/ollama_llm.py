# pipeline/providers/ollama_llm.py
from dataclasses import dataclass
from typing import Optional, Dict, Any
import requests

@dataclass
class OllamaLLM:
    model: str = "mistral"   # modèle local (peut être changé)
    endpoint: str = "http://localhost:11434/api/generate"

    def generate(self, prompt: str, *, max_tokens: int = 300, temperature: float = 0.2, context: str = "") -> Dict[str, Any]:
        """Appelle l’API locale Ollama et renvoie une réponse."""
        full_prompt = f"Contexte:\n{context}\n\nQuestion:\n{prompt}" if context else prompt
        payload = {
            "model": self.model,
            "prompt": full_prompt,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens
            },
            "stream": False
        }
        try:
            r = requests.post(self.endpoint, json=payload, timeout=60)
            r.raise_for_status()
            data = r.json()
            return {
                "text": data.get("response", ""),
                "usage": {
                    "model": self.model,
                    "provider": "ollama",
                    "eval_count": data.get("eval_count"),
                    "prompt_eval_count": data.get("prompt_eval_count"),
                }
            }
        except Exception as e:
            return {"text": f"[Erreur Ollama] {e}", "usage": {"error": str(e)}}