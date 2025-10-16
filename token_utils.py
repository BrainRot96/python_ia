# token_utils.py
from __future__ import annotations
import math
import re

# --- tiktoken (optionnel). Si absent, on bascule sur une heuristique chars/4.
try:
    import tiktoken  # type: ignore
    _HAS_TIKTOKEN = True
except Exception:
    tiktoken = None
    _HAS_TIKTOKEN = False


# Modèles connus -> nom d'encoding tiktoken
ENCODING_HINTS = {
    # OpenAI
    "gpt-4o": "o200k_base",
    "gpt-4o-mini": "o200k_base",
    "gpt-4.1": "o200k_base",
    "gpt-4-turbo": "cl100k_base",
    "gpt-3.5-turbo": "cl100k_base",
    # Mistral / Llama : à défaut, on utilise cl100k_base (approx raisonnable)
    "mistral": "cl100k_base",
    "mixtral": "cl100k_base",
    "llama": "cl100k_base",
}


def _encoding_for(model_hint: str | None) -> str:
    if not model_hint:
        return "cl100k_base"
    mh = model_hint.lower()
    for key, enc in ENCODING_HINTS.items():
        if key in mh:
            return enc
    return "cl100k_base"


def count_tokens(text: str, model_hint: str | None = None) -> int:
    """
    Compte (ou estime) les tokens pour `text`.
    - Si tiktoken dispo : encodage adapté au modèle si possible.
    - Sinon : heuristique ≈ len(chars)/4 (assez proche pour prompts FR/EN).
    """
    text = text or ""
    if not text:
        return 0

    if _HAS_TIKTOKEN:
        enc = tiktoken.get_encoding(_encoding_for(model_hint))
        return len(enc.encode(text))

    # Fallback heuristique
    # Bonus: on pénalise légèrement si beaucoup de ponctuation/emoji (≈ tokens ↑)
    base = math.ceil(len(text) / 4)
    punct = len(re.findall(r"[\,\.\:\;\!\?\(\)\[\]\{\}\-\_\/\\]", text))
    return int(base + punct * 0.05)


def estimate_cost(
    prompt_tokens: int,
    completion_tokens: int,
    price_in_per_1k: float = 0.0,
    price_out_per_1k: float = 0.0,
) -> float:
    """
    Estime le coût en $ (ou € si vous entrez des tarifs en €) :
    - price_in_per_1k : coût / 1000 tokens d'entrée
    - price_out_per_1k : coût / 1000 tokens de sortie
    """
    return (prompt_tokens / 1000.0) * price_in_per_1k + (completion_tokens / 1000.0) * price_out_per_1k