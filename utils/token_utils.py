# utils/token_utils.py — v2 (moteur d’optimisation amélioré, corrigé)
from __future__ import annotations

import math
import re
import unicodedata
from dataclasses import dataclass
from typing import Dict, Tuple, List

# ──────────────────────────────────────────────────────────────────────────────
# Profils modèles (heuristiques simples, hors-ligne)
# 1 token ~ 4 caractères (approx. FR/EN). Ajustable par modèle.
# ──────────────────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class ModelProfile:
    name: str
    chars_per_token: float = 4.0  # plus petit => plus de tokens pour un même texte

MODEL_PROFILES: Dict[str, ModelProfile] = {
    "mistral":     ModelProfile("mistral", chars_per_token=4.0),
    "llama3":      ModelProfile("llama3",  chars_per_token=4.2),
    "gpt-4o-mini": ModelProfile("gpt-4o-mini", chars_per_token=3.8),
}

DEFAULT_MODEL = "mistral"

# ──────────────────────────────────────────────────────────────────────────────
# Estimation de tokens (robuste, hors-ligne)
# ──────────────────────────────────────────────────────────────────────────────
def estimate_tokens(text: str, model: str = DEFAULT_MODEL) -> int:
    """
    Estime les tokens à partir du nombre de caractères visibles + un léger
    bonus pour la ponctuation/listes. Déterministe et hors-ligne.
    """
    text = text or ""
    prof = MODEL_PROFILES.get(model, MODEL_PROFILES[DEFAULT_MODEL])

    n_chars = len(text)
    tokens = math.ceil(n_chars / max(prof.chars_per_token, 1.0))

    # petit bonus pour la ponctuation / listes, souvent plus dense en tokens
    punct_bonus = text.count("\n") + text.count(";") + text.count(":")
    return max(0, tokens + math.floor(punct_bonus * 0.2))


def estimate_pair(prompt: str, context: str, model: str = DEFAULT_MODEL) -> Dict[str, int]:
    p = estimate_tokens(prompt, model)
    c = estimate_tokens(context, model)
    return {"prompt": p, "context": c, "total": p + c}

# ──────────────────────────────────────────────────────────────────────────────
# Règles de nettoyage / compression (purement déterministes)
# ──────────────────────────────────────────────────────────────────────────────
# Regex pré-compilées (publiques pour éviter des NameError si réutilisées)
SPACE_RE       = re.compile(r"[ \t]+")
MULTI_NL_RE    = re.compile(r"\n{3,}")
PUNCT_SPACE_RE = re.compile(r"\s*([,:;])\s*")
END_SPACE_DOT  = re.compile(r" +\.")
DUP_DASH_RE    = re.compile(r"( ?[-–—]{2,} ?)")
DUP_BULLET_RE  = re.compile(r"(\n[-•]\s*){2,}")

# salutations/mercis et politesses
HELLO_RE   = re.compile(r"(?m)^\s*(bonjour|salut|bonsoir)\b[ \t!.,:;–—-]*", re.IGNORECASE)
SIGNOFF_RE = re.compile(r"(?m)[ \t]*(merci(\s+beaucoup)?|cordialement|bien à vous)\b[ \t!.,:;–—-]*$", re.IGNORECASE)

POLITE_INLINE_RE = re.compile(
    r"\b(s['’]il (te|vous) plaît|svp|je (te|vous) prie|pouvez-vous|peux-tu)\b",
    re.IGNORECASE,
)
STP_RE = re.compile(r"\bstp\b", re.IGNORECASE)

# politesses / remplissage (soft)
_POLITENESSES: List[str] = [
    r"\b(s['’]il te plaît|s['’]il vous plaît|svp|merci d['’]avance)\b",
    r"\b(je te prie|je vous prie)\b",
]

_FILLERS: List[str] = [
    r"\b(en fait|du coup|au final|basiquement|clairement)\b",
    r"\b(vraiment|très|extrêmement|fortement)\b",
    r"\b(simplement|juste|un peu)\b",
]

# réécritures “safe” (réduction sans perte de sens)
_REWRITES: List[Tuple[re.Pattern, str]] = [
    # “est-ce que tu peux … ?” → “peux-tu … ?”
    (re.compile(r"\best[ -]?ce que tu peux\b", re.IGNORECASE), "peux-tu"),
    (re.compile(r"\best[ -]?ce que vous pouvez\b", re.IGNORECASE), "pouvez-vous"),
    # verbosité courante
    (re.compile(r"\bje voudrais\b", re.IGNORECASE), "je veux"),
    (re.compile(r"\bj’aimerais\b", re.IGNORECASE), "je veux"),
    # espaces autour de parenthèses
    (re.compile(r"\s*\(\s*"), "("),
    (re.compile(r"\s*\)\s*"), ") "),
]

# ──────────────────────────────────────────────────────────────────────────────
# Helpers de transformation
# ──────────────────────────────────────────────────────────────────────────────
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
    kept: List[str] = []
    for line in txt.splitlines():
        key = line.strip().lower()
        if key and key not in seen:
            kept.append(line)
            seen.add(key)
        elif not key and (not kept or kept[-1] != ""):
            kept.append("")  # conserve un seul blanc entre blocs
    return "\n".join(kept)


def _tighten(txt: str) -> str:
    out = SPACE_RE.sub(" ", txt)
    out = MULTI_NL_RE.sub("\n\n", out)
    out = PUNCT_SPACE_RE.sub(r"\1 ", out)  # “ , ” → “, ” etc.
    out = END_SPACE_DOT.sub(".", out)
    out = DUP_DASH_RE.sub(" — ", out)
    out = DUP_BULLET_RE.sub("\n- ", out)
    return out.strip()


def _smart_rewrite(txt: str) -> str:
    out = txt
    for pat, repl in _REWRITES:
        out = pat.sub(repl, out)
    return out


def _strip_greetings_and_polite(txt: str) -> str:
    """
    Supprime 'bonjour/salut/bonsoir' en début de ligne,
    'merci/cordialement...' en fin de ligne, et politesses inline (svp, stp, etc.).
    """
    out = txt
    out = HELLO_RE.sub("", out)
    out = SIGNOFF_RE.sub("", out)
    out = POLITE_INLINE_RE.sub("", out)
    out = STP_RE.sub("", out)
    return _tighten(out)


def _final_clean(txt: str) -> str:
    """
    Nettoyage de finition : espaces multiples, espaces autour de la ponctuation,
    ponctuation traînante, lignes vides excédentaires.
    """
    out = re.sub(r"[ \t]{2,}", " ", txt)
    out = re.sub(r"\s*([,:;!?])\s*", r"\1 ", out)     # “ , ” → “, ”
    out = re.sub(r"\s*\.\s*", ". ", out)              # “ . ” → “. ”
    out = re.sub(r"\s*\n\s*", "\n", out)              # espaces autour des sauts de ligne
    out = re.sub(r"(?:[ ,;:.!?])+(\n|$)", r"\1", out) # ponctuation traînante
    out = MULTI_NL_RE.sub("\n\n", out)                # max 2 sauts consécutifs
    return out.strip()

# Raccourcis ciblés pour formulations fréquentes en français
_SHORTEN_PATTERNS: List[Tuple[re.Pattern, str]] = [
    # Résumé
    (re.compile(r"\bfais[ -]?moi un\s+résumé(\s+(rapide|court))?\s+de\b", re.IGNORECASE), "résume "),
    (re.compile(r"\bpeux[- ]?tu\s+me\s+faire\s+un\s+résumé\s+de\b", re.IGNORECASE), "résume "),
    (re.compile(r"\best[- ]?ce\s+que\s+tu\s+peux\s+(me\s+)?faire\s+un\s+résumé\s+de\b", re.IGNORECASE), "résume "),

    # "n'hésite pas à" → (supprimé)
    (re.compile(r"\bn['’]hésite\s+pas\s+à\s+", re.IGNORECASE), ""),

    # Détails / style
    (re.compile(r"\bdétails\s+poignants\b", re.IGNORECASE), "détails marquants"),
    (re.compile(r"\bje\s+vais\s+faire\s+un\s+discours\b", re.IGNORECASE), "style discours"),
    (re.compile(r"\b(raconter|présenter)\s+(devant|à)\s+(tout\s+le\s+monde|le\s+public)\b", re.IGNORECASE), "style public"),

    # Par rapport à → sur
    (re.compile(r"\bpar\s+rapport\s+à\b", re.IGNORECASE), "sur"),
]

# Normalisations compactes de contraintes
_CONSTRAINT_PATTERNS: List[Tuple[re.Pattern, str]] = [
    # "en trois parties distinctes" → "en 3 parties"
    (re.compile(r"\ben\s+(trois|3)\s+parties?(\s+distinctes?)?\b", re.IGNORECASE), "en 3 parties"),
    # Variantes « trois partie » mal accordées
    (re.compile(r"\b(trois)\s+partie\b", re.IGNORECASE), "3 parties"),
]

_DEFECT_FIXES: List[Tuple[re.Pattern, str]] = [
    # Typos fréquentes
    (re.compile(r"\bej\s+vais\b", re.IGNORECASE), "je vais"),
]

def _shorten_common_phrases(txt: str) -> str:
    out = txt
    for pat, repl in _SHORTEN_PATTERNS:
        out = pat.sub(repl, out)
    for pat, repl in _CONSTRAINT_PATTERNS:
        out = pat.sub(repl, out)
    for pat, repl in _DEFECT_FIXES:
        out = pat.sub(repl, out)
    # Compacte « trois » → « 3 » quand suivi de « parties »
    out = re.sub(r"\btrois(?=\s+parties?\b)", "3", out, flags=re.IGNORECASE)
    return out

# Corrections légères (sans LLM)
LITE_FIXES: List[Tuple[re.Pattern, str]] = [
    (re.compile(r"\bstp\b", re.IGNORECASE), "s'il te plaît"),
    (re.compile(r"\bj ?ai\b", re.IGNORECASE), "j'ai"),
    (re.compile(r"\s+à\s+| a ", re.IGNORECASE), " à "),  # normalise les espaces autour de "à"
    (re.compile(r"\bIA\b"), "IA"),
    (re.compile(r"\bgpt\b", re.IGNORECASE), "GPT"),
    (re.compile(r"\bortographe\b", re.IGNORECASE), "orthographe"),
]

def _lite_spell(txt: str) -> str:
    out = txt
    for pat, repl in LITE_FIXES:
        out = pat.sub(repl, out)
    return out


def _normalize_unicode(txt: str) -> str:
    # NFKC: compatibilité/largeur homogène ; garde les accents
    return unicodedata.normalize("NFKC", txt or "")

# ──────────────────────────────────────────────────────────────────────────────
# Optimiseur principal (déterministe, sans LLM)
# ──────────────────────────────────────────────────────────────────────────────
def optimize_prompt(
    text: str,
    *,
    model: str = DEFAULT_MODEL,
    budget_tokens: int | None = None,
    aggressive: bool = False,
    lite_spell: bool = False,
) -> Tuple[str, Dict[str, object]]:
    """
    Optimise un prompt de façon déterministe (sans LLM).
    - aggressive=True : supprime aussi les salutations/clôtures.
    - budget_tokens : si fourni, on pousse davantage la compression
      tant que l’estimation > budget (sans changer le sens).
    - lite_spell : applique quelques corrections légères (typos fréquentes).
    Retourne (prompt_optimisé, stats).
    """
    original = _normalize_unicode(text or "")
    out = original.strip()

    steps: List[str] = []

    # 0) correction légère optionnelle
    if lite_spell:
        new = _lite_spell(out)
        if new != out:
            steps.append("lite_spell")
        out = new

    # 1) Nettoyage “soft”
    new = _strip_greetings_and_polite(out)
    if new != out: steps.append("strip_greetings_polite")
    out = new

    new = _strip_fillers(out)
    if new != out: steps.append("strip_fillers")
    out = new

    new = _smart_rewrite(out)
    if new != out: steps.append("smart_rewrite")
    out = new

    new = _shorten_common_phrases(out)
    if new != out: steps.append("shorten_common")
    out = new

    new = _dedupe_lines(out)
    if new != out: steps.append("dedupe_lines")
    out = new

    new = _tighten(out)
    if new != out: steps.append("tighten")
    out = new

    # 2) Mode agressif (recoupe salutations / clôtures au cas où)
    if aggressive:
        new = HELLO_RE.sub("", out)
        if new != out: steps.append("cut_hello")
        out = new

        new = SIGNOFF_RE.sub("", out)
        if new != out: steps.append("cut_signoff")
        out = new

        out = _tighten(out)

    # 3) Si budget imposé, tente de compresser davantage (itératif)
    if budget_tokens is not None and budget_tokens > 0:
        tries = 0
        while estimate_tokens(out, model) > budget_tokens and tries < 3:
            tries += 1
            before = out
            out = HELLO_RE.sub("", out)
            out = SIGNOFF_RE.sub("", out)
            out = re.sub(r"\b(je veux|je souhaiterais|j’aimerais)\b", "je veux", out, flags=re.IGNORECASE)
            out = re.sub(r"\b(par rapport à)\b", "sur", out, flags=re.IGNORECASE)
            out = re.sub(r"\b(un peu|plutôt|assez)\b", "", out, flags=re.IGNORECASE)
            out = _tighten(out)
            if out == before:
                break
            steps.append(f"budget_pass_{tries}")

    # 4) Polissage final
    out = _final_clean(out)
    steps.append("final_clean")

    # Stats
    before_chars = len(original)
    after_chars  = len(out)
    before_tok   = estimate_tokens(original, model)
    after_tok    = estimate_tokens(out, model)

    stats: Dict[str, object] = {
        "model": model,
        "chars_before": before_chars,
        "chars_after": after_chars,
        "chars_saved": max(0, before_chars - after_chars),
        "pct_saved": 0 if before_chars == 0 else round((before_chars - after_chars) * 100 / before_chars, 1),
        "tokens_before": before_tok,
        "tokens_after": after_tok,
        "tokens_saved": max(0, before_tok - after_tok),
        "steps": steps,
        "respected_budget": (budget_tokens is None) or (after_tok <= budget_tokens),
        "budget_tokens": budget_tokens,
    }
    return out.strip(), stats

# ──────────────────────────────────────────────────────────────────────────────
# Structuration optionnelle (JSON « mini » que le LLM peut suivre)
# ──────────────────────────────────────────────────────────────────────────────
def wrap_as_structured_instruction(
    instruction: str,
    fields=("objectif", "contraintes", "format_sortie")
) -> str:
    tmpl = [
        "Rôle: Assistant concis et précis.",
        "Tâche:",
        (instruction or "").strip(),
        "",
        "Réponds en JSON avec les clés suivantes:",
        "{",
    ]
    for f in fields:
        tmpl.append(f'  "{f}": "..."')
    tmpl.append("}")
    return "\n".join(tmpl)
