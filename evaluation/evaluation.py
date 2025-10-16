# evaluation/evaluation.py
import os
import json
from datetime import datetime
from typing import List, Dict, Any, Optional

# Dossier et fichier de logs
LOG_DIR = "data"
LOG_FILE = os.path.join(LOG_DIR, "log.jsonl")

# Crée automatiquement le dossier data/
os.makedirs(LOG_DIR, exist_ok=True)


def log_event(event: Dict[str, Any]) -> None:
    """
    Enregistre un événement (entrée/sortie LLM) dans un fichier JSONL.
    Chaque ligne = 1 événement.
    """
    event["timestamp"] = datetime.utcnow().isoformat()
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")


def read_events(limit: Optional[int] = None) -> List[Dict[str, Any]]:
    """Lit le fichier log.jsonl et renvoie une liste d'événements (dictionnaires)."""
    if not os.path.exists(LOG_FILE):
        return []

    events = []
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        for line in f:
            try:
                events.append(json.loads(line))
            except Exception:
                continue

    if limit:
        return events[-limit:]
    return events


def to_dataframe(events: List[Dict[str, Any]]):
    """
    Convertit la liste d'événements en DataFrame (si pandas est installé),
    sinon retourne None.
    """
    try:
        import pandas as pd
        df = pd.json_normalize(events, sep=".")
        preferred_cols = [
            "timestamp", "provider", "model",
            "params.temperature", "params.max_tokens",
            "input.query", "input.context",
            "output.text",
            "usage.prompt_tokens", "usage.completion_tokens", "usage.total_tokens",
        ]
        cols = [c for c in preferred_cols if c in df.columns] + [
            c for c in df.columns if c not in preferred_cols
        ]
        return df[cols]
    except ImportError:
        return None