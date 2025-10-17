
# utils/prefs.py
from __future__ import annotations
import json, os
from dataclasses import dataclass, asdict
from typing import Any, Dict

CONFIG_DIR  = os.path.expanduser("~/.botanai")
CONFIG_FILE = os.path.join(CONFIG_DIR, "optimizer_prefs.json")

DEFAULTS: Dict[str, Any] = {
    "theme_choice": "Auto",        # Auto | Clair | Sombre
    "model": "mistral",            # clé de MODEL_PROFILES
    "budget_on": False,
    "budget": 300,
    "aggressive": False,
    "add_constraint": True,
    "lite_spell": True,
    "n_points": 5,
    "max_words": 120,
    "ultra_compact": False,
}

def load_prefs() -> Dict[str, Any]:
    try:
        if not os.path.exists(CONFIG_FILE):
            return DEFAULTS.copy()
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        # merge avec defaults (au cas où on ajoute des clés)
        out = DEFAULTS.copy()
        out.update({k: data.get(k, v) for k, v in DEFAULTS.items()})
        return out
    except Exception:
        return DEFAULTS.copy()

def save_prefs(prefs: Dict[str, Any]) -> None:
    os.makedirs(CONFIG_DIR, exist_ok=True)
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(prefs, f, ensure_ascii=False, indent=2)
    except Exception:
        # on ignore calmement si le disque est en lecture seule
        pass