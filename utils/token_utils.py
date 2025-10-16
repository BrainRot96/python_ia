# utils/token_utils.py
from __future__ import annotations
import math, re
from dataclasses import dataclass
from typing import Dict, Tuple

# ——————————————————————————————————————————————————————————
# Profils modèles (heuristiques simples, pas besoin d'Internet)
# 1 token ~ 4 caractères en moyenne (fr/en), c’est une approximation.
# ——————————————————————————————————————————————————————————
@dataclass(frozen=True)
class ModelProfile:
    name: str
    chars_per_token: float = 4.0  # plus petit => plus de tokens pour un même texte

MODEL_PROFILES: Dict[str, ModelProfile] = {
    "mistral":    ModelProfile("mistral", chars_per_token=4.0),
    "llama3":     ModelProfile("llama3",  chars_per_token=4.2),
    "gpt-4o-mini":ModelProfile("gpt-4o-mini", chars_per_token=3.8),
}

DEFAULT_MODEL = "mistral"

# ——————————————————————————————————————————————————————————
# Estimation de tokens (très simple et robuste hors-ligne)
# ——————————————————————————————————————————————————————————
def estimate_tokens(text: str, model: str = DEFAULT_MODEL) -> int:
    text = text or ""
    prof = MODEL_PROFILES.get(model, MODEL_PROFILES[DEFAULT_MODEL])
    # heuristique : compte caractères visibles
    n_chars = len(text)
    tokens = math.ceil(n_chars / max(prof.chars_per_token, 1.0))
    # petit bonus pour la ponctuation lourde / listes
    # (ça capte souvent des structures qui 'tokenisent' plus dense)
    punct_bonus = text.count("\n") + text.count(";") + text.count(":")
    return max(0, tokens + math.floor(punct_bonus * 0.2))

def estimate_pair(prompt: str, context: str, model: str = DEFAULT_MODEL) -> Dict[str, int]:
    p = estimate_tokens(prompt, model)
    c = estimate_tokens(context, model)
    return {"prompt": p, "context": c, "total": p + c}

# ——————————————————————————————————————————————————————————
# Règles d’optimisation (purement déterministes)
# Objectif : réduire la taille sans changer le sens.
# ——————————————————————————————————————————————————————————
_POLITENESSES = [
    r"\b(s'il te plaît|s'il vous plaît|svp|merci d'avance)\b",
    r"\b(je te prie|je vous prie)\b",
    r"\b(pouvez-vous|peux-tu)\b",
]
_FILLERS = [
    r"\b(en fait|du coup|du coups|au final|basiquement|clairement)\b",
    r"\b(vraiment|très|extrêmement|fortement)\b",
    r"\b(simplement|juste)\b",
]
_SPACE_RE = re.compile(r"[ \t]+")
_MULTI_NL_RE = re.compile(r"\n{3,}")

def _strip_politeness(txt: str) -> str:
    out = txt
    for rx in _POLITENESSES:
        out = re.sub(rx, "", out, flags=re.IGNORECASE)
    return out

def _strip_fillers(txt: str) -> str:
    out = txt
    for rx in _FILLERS:
        out = re.sub(rx, "", out, flags=re.IGNORECASE)
    return out

def _dedupe_lines(txt: str) -> str:
    seen = set()
    kept = []
    for line in txt.splitlines():
        key = line.strip().lower()
        if key and key not in seen:
            kept.append(line)
            seen.add(key)
        elif not key and (not kept or kept[-1] != ""):
            # conserve un seul blanc entre blocs
            kept.append("")
    return "\n".join(kept)

def _tighten(txt: str) -> str:
    # compresse les espaces multiples, nettoie ponctuation
    out = SPACE_RE.sub(" ", txt)
    out = _MULTI_NL_RE.sub("\n\n", out)
    out = re.sub(r" ?([,:;]) ?", r"\1 ", out)
    out = re.sub(r" +\.", ".", out)
    return out.strip()

def optimize_prompt(text: str) -> Tuple[str, Dict[str, int]]:
    """Applique des règles simples et retourne (texte_opt, stats)."""
    original = text or ""
    before = len(original)

    out = original.strip()
    out = _strip_politeness(out)
    out = _strip_fillers(out)
    out = _dedupe_lines(out)
    out = _tighten(out)

    after = len(out)
    stats = {
        "chars_before": before,
        "chars_after": after,
        "chars_saved": max(0, before - after),
        "pct_saved": 0 if before == 0 else round((before - after) * 100 / before, 1),
    }
    return out, stats

# ——————————————————————————————————————————————————————————
# Structuration (optionnelle) en JSON mini
# ——————————————————————————————————————————————————————————
def wrap_as_structured_instruction(instruction: str, fields=("objectif","contraintes","format_sortie")) -> str:
    tmpl = [
        "Rôle: Assistant concis et précis.",
        "Tâche:",
        instruction.strip(),
        "",
        "Réponds en JSON avec les clés suivantes:",
        "{",
    ]
    for f in fields:
        tmpl.append(f'  "{f}": "..."')
    tmpl.append("}")
    return "\n".join(tmpl)
