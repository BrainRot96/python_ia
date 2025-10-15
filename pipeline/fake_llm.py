# pipeline/fake_llm.py
from dataclasses import dataclass
import re, random
from typing import Dict, Any, List

@dataclass
class FakeCompletion:
    text: str
    usage: Dict[str, int]

class FakeLLM:
    """
    Un modèle factice (FakeLLM) qui simule une génération de texte.
    Il ne fait pas appel à un vrai modèle de langage — parfait pour tester le pipeline.
    """
    def __init__(self, seed: int = 42):
        self.rng = random.Random(seed)

    def _sentences(self, text: str) -> List[str]:
        """Découpe un texte en phrases simples."""
        return [s for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s]

    def generate(self, prompt: str, *, max_tokens: int = 256, temperature: float = 0.2) -> Dict[str, Any]:
        """Simule la génération de texte à partir d'un prompt."""
        body = prompt.strip()

        # Si le mot "résume" apparaît → mode résumé
        if "résume" in body.lower() or "résumé" in body.lower():
            sents = self._sentences(body)
            out = " ".join((sents[-5:] or [body])[:3])
            text = f"Résumé (fake): {out[: max_tokens*4]}"
        else:
            # Sinon, mode “réponse générale”
            words = re.findall(r"\w+", body.lower())
            keys = ", ".join(sorted(set(words))[:8])
            text = "Réponse (fake): Réponse courte. Mots-clés: " + keys

        # Données d’usage simulées (comme une vraie API)
        usage = {
            "prompt_tokens": min(4096, len(body)//4 + 1),
            "completion_tokens": min(max_tokens, max(16, len(text)//4)),
        }
        usage["total_tokens"] = usage["prompt_tokens"] + usage["completion_tokens"]

        # Retourne un dictionnaire identique à ce qu'un vrai LLM renverrait
        return FakeCompletion(text=text, usage=usage).__dict__
    