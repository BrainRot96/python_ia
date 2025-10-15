# pipeline/fake_llm.py
import random
from dataclasses import dataclass
from typing import Dict, Any

@dataclass
class FakeLLM:
    """LLM factice pour les tests — ne fait que renvoyer des réponses simulées."""
    seed: int = 42

    def generate(self, prompt: str, max_tokens: int = 128, temperature: float = 0.5, context: str = "") -> Dict[str, Any]:
        """Simule la génération de texte avec prise en compte optionnelle du contexte."""
        random.seed(self.seed)
        fake_response = ""

        # Si le mot "résume" est présent dans le prompt, on fait semblant de résumer
        if "résume" in prompt.lower():
            fake_response = (
                f"Résumé (fake): {context[:120]}..." if context else "Résumé simulé : le texte est synthétisé."
            )
        else:
            exemples = [
                "Le tournesol suit le soleil du matin au soir.",
                "Les abeilles jouent un rôle essentiel dans la pollinisation.",
                "Le chêne est un arbre symbole de force et de longévité.",
                "Les papillons reconnaissent les fleurs par leur couleur et leur parfum.",
            ]
            fake_response = random.choice(exemples)

        return {
            "text": fake_response,
            "usage": {
                "model": "FakeLLM",
                "provider": "mock",
                "eval_count": random.randint(5, 30),
                "prompt_eval_count": random.randint(1, 5),
            },
        }