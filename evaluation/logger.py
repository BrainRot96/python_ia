# evaluation/logger.py
from __future__ import annotations
import os, json, uuid, datetime as dt
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------
# Configuration des chemins
# ---------------------------------------------------------------------
LOG_DIR  = "data"
LOG_FILE = os.path.join(LOG_DIR, "log.jsonl")

# ---------------------------------------------------------------------
# Utilitaires internes
# ---------------------------------------------------------------------
def _ensure_dir() -> None:
    """Crée le dossier data/ si besoin."""
    os.makedirs(LOG_DIR, exist_ok=True)

# ---------------------------------------------------------------------
# Fonction principale d’écriture
# ---------------------------------------------------------------------
def log_event(event: Dict[str, Any], rating: Optional[int] = None, log_path: str = LOG_FILE) -> str:
    """
    Ajoute un événement dans le fichier JSONL (log.jsonl).
    Chaque ligne = un dict JSON indépendant.
    """
    _ensure_dir()
    e = dict(event)
    e.setdefault("id", str(uuid.uuid4()))
    e.setdefault("ts", dt.datetime.utcnow().isoformat(timespec="seconds") + "Z")
    if rating is not None:
        e["rating"] = int(rating)

    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    except Exception as err:
        print(f"[logger] Erreur écriture: {err}")
    return e["id"]

# ---------------------------------------------------------------------
# Lecture du fichier de logs
# ---------------------------------------------------------------------
def read_events(log_path: str = LOG_FILE, limit: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Lit le fichier JSONL et retourne une liste de dicts (événements).
    - log_path : chemin vers le fichier
    - limit : nombre max d'événements (à partir de la fin)
    """
    if not os.path.exists(log_path):
        return []

    events: List[Dict[str, Any]] = []
    with open(log_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except Exception:
                continue

    if limit is not None and isinstance(limit, int):
        return events[-limit:]
    return events

# ---------------------------------------------------------------------
# Conversion en DataFrame (optionnel)
# ---------------------------------------------------------------------
def to_dataframe(events: List[Dict[str, Any]]):
    """
    Convertit la liste d'événements en DataFrame si pandas est installé.
    """
    try:
        import pandas as pd
    except Exception:
        return None

    if not events:
        return pd.DataFrame()

    flat = []
    for e in events:
        flat.append({
            "id": e.get("id"),
            "ts": e.get("ts"),
            "provider": e.get("provider"),
            "model": e.get("model"),
            "temperature": e.get("params", {}).get("temperature"),
            "max_tokens": e.get("params", {}).get("max_tokens"),
            "query": e.get("input", {}).get("query", ""),
            "context": e.get("input", {}).get("context", ""),
            "output": e.get("output", {}).get("text", ""),
            "usage": e.get("usage"),
            "rating": e.get("rating", None),
        })
    return pd.DataFrame(flat)