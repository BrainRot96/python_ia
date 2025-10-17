# prompts/optimizer_smart.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, Optional, Tuple

# Petit estimateur de tokens (approx) si tu n'as pas de tokenizer :
def estimate_tokens(text: str) -> int:
    # assez correct pour comparer avant/après
    # (espaces / ponctuation comptent peu, on segmente "mot-ish")
    return max(1, len(text.strip().split()))

SMART_SYSTEM = (
    "Tu es un assistant qui REFORMULE des prompts pour LLM. "
    "Objectif: réduire le nombre de tokens, garder l'intention, supprimer le superflu, "
    "préciser les contraintes utiles (format, longueur) sans ajouter d'explications."
)

SMART_USER_TEMPLATE = """\
Réécris le prompt ci-dessous pour qu'il soit plus court, explicite et exploitable par un LLM,
sans changer l'intention. Supprime la politesse / le contexte inutile. Si pertinent, ajoute
une CONTRAINTE DE FORME (ex: «réponds en X points concis», «≤ {max_words} mots»).

Contrainte de longueur (souhaitée, non obligatoire): sortie ≤ ~{target_tokens} tokens.

Prompt d'origine:
----
{raw}
----
Rends uniquement le prompt réécrit, rien d'autre.
"""

@dataclass
class SmartOptimizeResult:
    optimized: str
    tokens_in: int
    tokens_out: int
    gain_tokens: int

def smart_optimize_prompt(
    llm,                       # instance avec .generate(prompt=..., max_tokens=..., temperature=...)
    raw_prompt: str,
    target_tokens: int = 120,
    max_words: int = 120,
    temperature: float = 0.2,
    max_tokens: int = 256,
) -> SmartOptimizeResult:
    # 1) Construire le "super-prompt"
    user = SMART_USER_TEMPLATE.format(
        raw=raw_prompt.strip(),
        target_tokens=target_tokens,
        max_words=max_words,
    )
    full = f"{SMART_SYSTEM}\n\n{user}"

    # 2) Appel Ollama (ou tout LLM compatible)
    resp = llm.generate(
        prompt=full,
        max_tokens=max_tokens,
        temperature=temperature,
        context=""   # on force vide pour un comportement déterministe
    )
    text = resp.get("text", "").strip()

    # 3) Estimation avant/après
    t_in  = estimate_tokens(raw_prompt)
    t_out = estimate_tokens(text)
    return SmartOptimizeResult(
        optimized=text,
        tokens_in=t_in,
        tokens_out=t_out,
        gain_tokens=t_in - t_out,
    )