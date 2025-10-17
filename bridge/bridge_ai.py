# bridge/bridge_ai.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, Literal, Optional

from pipeline.providers.openai_llm import OpenAILLM
from pipeline.providers.anthropic_llm import AnthropicLLM

ChainMode = Literal["claude_then_gpt", "gpt_then_claude", "solo_gpt", "solo_claude"]

@dataclass
class BridgeConfig:
    openai_model: str = "gpt-4o-mini"
    anthropic_model: str = "claude-3-5-sonnet-20240620"
    temperature: float = 0.2
    max_tokens: int = 300

class BridgeOrchestrator:
    def __init__(self, cfg: Optional[BridgeConfig] = None):
        self.cfg = cfg or BridgeConfig()
        self.gpt = OpenAILLM(model=self.cfg.openai_model)
        self.claude = AnthropicLLM(model=self.cfg.anthropic_model)

    def run(
        self,
        prompt: str,
        *,
        mode: ChainMode = "claude_then_gpt",
        system_first: str | None = None,
        system_second: str | None = None,
    ) -> Dict[str, Any]:
        """
        Exécute selon le mode choisi :
        - claude_then_gpt : Claude produit un brouillon → GPT polit/synthétise
        - gpt_then_claude : GPT brouillon → Claude structure/critique
        - solo_gpt / solo_claude : un seul modèle
        Retourne {text, steps, usage}
        """
        steps = []
        usage_total = {}

        if mode == "solo_gpt":
            r1 = self.gpt.generate(prompt, max_tokens=self.cfg.max_tokens,
                                   temperature=self.cfg.temperature, system=system_first)
            steps.append({"provider": "openai", "text": r1["text"], "usage": r1.get("usage", {})})
            return {"text": r1["text"], "steps": steps, "usage": r1.get("usage", {})}

        if mode == "solo_claude":
            r1 = self.claude.generate(prompt, max_tokens=self.cfg.max_tokens,
                                      temperature=self.cfg.temperature, system=system_first)
            steps.append({"provider": "anthropic", "text": r1["text"], "usage": r1.get("usage", {})})
            return {"text": r1["text"], "steps": steps, "usage": r1.get("usage", {})}

        if mode == "claude_then_gpt":
            r1 = self.claude.generate(
                f"Ébauche initiale.\n\nQuestion/utilisateur :\n{prompt}",
                max_tokens=self.cfg.max_tokens,
                temperature=self.cfg.temperature,
                system=system_first or "Tu produis un brouillon structuré et factuel, en français."
            )
            steps.append({"provider": "anthropic", "text": r1["text"], "usage": r1.get("usage", {})})

            r2 = self.gpt.generate(
                f"Améliore, clarifie et condense le texte suivant sans perdre d'information :\n\n{r1['text']}",
                max_tokens=self.cfg.max_tokens,
                temperature=self.cfg.temperature,
                system=system_second or "Tu es un excellent éditeur : clair, concis, et précis. Réponds en français."
            )
            steps.append({"provider": "openai", "text": r2["text"], "usage": r2.get("usage", {})})
            return {"text": r2["text"], "steps": steps, "usage": {"first": r1.get("usage"), "second": r2.get("usage")}}

        if mode == "gpt_then_claude":
            r1 = self.gpt.generate(
                f"Brouillon initial.\n\nQuestion/utilisateur :\n{prompt}",
                max_tokens=self.cfg.max_tokens,
                temperature=self.cfg.temperature,
                system=system_first or "Tu produis un brouillon utile, en français."
            )
            steps.append({"provider": "openai", "text": r1["text"], "usage": r1.get("usage", {})})

            r2 = self.claude.generate(
                f"Analyse le brouillon suivant, corrige, structure, et améliore la rigueur :\n\n{r1['text']}",
                max_tokens=self.cfg.max_tokens,
                temperature=self.cfg.temperature,
                system=system_second or "Tu es un réviseur méticuleux, factuel, structuré. Réponds en français."
            )
            steps.append({"provider": "anthropic", "text": r2["text"], "usage": r2.get("usage", {})})
            return {"text": r2["text"], "steps": steps, "usage": {"first": r1.get("usage"), "second": r2.get("usage")}}

        # fallback
        return {"text": "", "steps": steps, "usage": {}}
    