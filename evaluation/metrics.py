# evaluation/metrics.py
from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple
from collections import Counter, defaultdict
from datetime import datetime

# ------------------------------------------------------------
# Helpers internes
# ------------------------------------------------------------
def _get_usage_tokens(e: Dict[str, Any]) -> Tuple[Optional[int], Optional[int], Optional[int]]:
    """
    Récupère prudemment (prompt_tokens, completion_tokens, total_tokens)
    depuis e["usage"] si disponible.
    """
    usage = e.get("usage") or {}
    pt = usage.get("prompt_tokens")
    ct = usage.get("completion_tokens")
    tt = usage.get("total_tokens")
    # Si total_tokens absent mais pt/ct présents, on le calcule
    if tt is None and isinstance(pt, int) and isinstance(ct, int):
        tt = pt + ct
    return pt if isinstance(pt, int) else None, \
           ct if isinstance(ct, int) else None, \
           tt if isinstance(tt, int) else None

def _safe_str(v: Any) -> str:
    return str(v) if v is not None else ""

def _parse_ts(e: Dict[str, Any]) -> Optional[datetime]:
    """
    Essaye de parser un timestamp:
    - champs possibles: "ts" (ex: 2025-10-15T14:12:03Z) ou "timestamp"
    - retourne None si parse impossible.
    """
    ts = e.get("ts") or e.get("timestamp")
    if not ts or not isinstance(ts, str):
        return None

    # Formats tentés (les deux plus courants dans nos logs)
    # 1) 2025-10-15T14:12:03Z
    # 2) 2025-10-15T14:12:03.123456Z
    # 3) 2025-10-15T14:12:03 (sans Z)
    for fmt in ("%Y-%m-%dT%H:%M:%SZ",
                "%Y-%m-%dT%H:%M:%S.%fZ",
                "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(ts, fmt)
        except Exception:
            continue
    # dernier recours: tentative très permissive
    try:
        # Ex: "2025-10-15T14:12:03.123456"
        return datetime.fromisoformat(ts.replace("Z", ""))
    except Exception:
        return None

# ------------------------------------------------------------
# KPIs principaux (résumé global)
# ------------------------------------------------------------
def basic_kpis(events: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Retourne un dict de KPI globaux:
    {
      "runs": <int>,
      "feedback": {"positive": <int>, "negative": <int>, "neutral": <int>},
      "avg_tokens": {"prompt": <float>, "completion": <float>, "total": <float>},
      "providers": {"Ollama": 10, "FakeLLM": 5, ...},
      "models": {"mistral": 8, "fake-llm": 7, ...}
    }
    """
    n = len(events)
    providers = Counter()
    models = Counter()

    # feedback: -1 / 0 / 1
    fb_pos = fb_neg = fb_neu = 0

    prompt_sum = completion_sum = total_sum = 0
    prompt_n = completion_n = total_n = 0

    for e in events:
        providers[_safe_str(e.get("provider"))] += 1
        models[_safe_str(e.get("model"))] += 1

        rating = e.get("rating", None)
        if rating == 1:
            fb_pos += 1
        elif rating == -1:
            fb_neg += 1
        else:
            fb_neu += 1

        pt, ct, tt = _get_usage_tokens(e)
        if pt is not None:
            prompt_sum += pt
            prompt_n += 1
        if ct is not None:
            completion_sum += ct
            completion_n += 1
        if tt is not None:
            total_sum += tt
            total_n += 1

    def _avg(s: int, k: int) -> float:
        return (s / k) if k > 0 else 0.0

    return {
        "runs": n,
        "feedback": {
            "positive": fb_pos,
            "negative": fb_neg,
            "neutral": fb_neu,
        },
        "avg_tokens": {
            "prompt": _avg(prompt_sum, prompt_n),
            "completion": _avg(completion_sum, completion_n),
            "total": _avg(total_sum, total_n),
        },
        "providers": dict(providers),
        "models": dict(models),
    }

# ------------------------------------------------------------
# Tokens moyens par provider (pour bar chart)
# ------------------------------------------------------------
def tokens_by_provider(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Renvoie une liste de lignes: [{"provider": "...", "avg_tokens": 123.4}, ...]
    Calcul sur total_tokens quand disponible, sinon (prompt+completion).
    """
    agg_sum = defaultdict(int)   # somme des tokens
    agg_cnt = defaultdict(int)   # nb d'échantillons

    for e in events:
        prov = _safe_str(e.get("provider"))
        _, _, tt = _get_usage_tokens(e)
        if tt is not None:
            agg_sum[prov] += tt
            agg_cnt[prov] += 1

    rows = []
    for prov, s in agg_sum.items():
        c = agg_cnt.get(prov, 0)
        if c > 0:
            rows.append({"provider": prov, "avg_tokens": s / c})
    # tri décroissant (optionnel)
    rows.sort(key=lambda r: r["avg_tokens"], reverse=True)
    return rows

# ------------------------------------------------------------
# Évolution des runs au cours du temps
# ------------------------------------------------------------
def runs_over_time(events: List[Dict[str, Any]], bucket: str = "day") -> List[Dict[str, Any]]:
    """
    Agrège le nombre de runs par jour (bucket='day') ou par heure (bucket='hour').

    Retour: [{"date": "2025-10-15", "runs": 7}, ...]  (day)
            [{"date": "2025-10-15 14:00", "runs": 3}, ...]  (hour)
    """
    buckets = Counter()

    for e in events:
        t = _parse_ts(e)
        if not t:
            continue
        if bucket == "hour":
            key = t.strftime("%Y-%m-%d %H:00")
        else:  # "day" par défaut
            key = t.strftime("%Y-%m-%d")
        buckets[key] += 1

    rows = [{"date": k, "runs": v} for k, v in buckets.items()]
    # tri chronologique
    rows.sort(key=lambda r: r["date"])
    return rows