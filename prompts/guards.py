# prompts/guards.py
from __future__ import annotations
from typing import Tuple, Optional

# Estimation simple : ~4 caractères ≈ 1 token
AVG_CHARS_PER_TOKEN = 4

def estimate_tokens(text: str) -> int:
    """Estime grossièrement le nombre de tokens d'un texte."""
    return max(1, int(len(text) / AVG_CHARS_PER_TOKEN))

def enforce_limits(
    text: str,
    *,
    max_tokens: Optional[int] = None,
    max_chars: Optional[int] = None
) -> Tuple[str, bool]:
    """
    Coupe `text` pour respecter des limites simples.
    Retourne (texte_coupé, was_cut: bool).
    - Si max_tokens est donné, on convertit en limite caractères (≈ tokens*4).
    - Si max_chars est donné aussi, on prend la plus stricte des deux.
    """
    if max_tokens is None and max_chars is None:
        return text, False

    limit_chars = None
    if max_chars is not None:
        limit_chars = max_chars
    if max_tokens is not None:
        token_chars = max_tokens * AVG_CHARS_PER_TOKEN
        limit_chars = min(limit_chars, token_chars) if limit_chars else token_chars

    # Rien à couper
    if limit_chars is None or len(text) <= limit_chars:
        return text, False

    clipped = text[:limit_chars]

    # Évite de couper au milieu d’un mot / phrase si possible
    tail_window = 200
    last_nl = clipped.rfind("\n")
    if last_nl != -1 and last_nl >= limit_chars - tail_window:
        clipped = clipped[:last_nl]
    else:
        last_space = clipped.rfind(" ")
        if last_space != -1 and last_space >= limit_chars - tail_window:
            clipped = clipped[:last_space]

    return clipped, True