# dashboard_logs.py
# Mini dashboard d'analyse des logs JSONL produits par app_streamlit.py
# Lance:  python -m streamlit run dashboard_logs.py

from __future__ import annotations
import json, os
from pathlib import Path
from typing import Any, Dict, List, Optional

import streamlit as st

# --- Config ---
LOG_DIR  = "data"
LOG_FILE = os.path.join(LOG_DIR, "log.jsonl")

st.set_page_config(page_title="Dashboard logs LLM", page_icon="📊", layout="wide")
st.title("📊 Dashboard — Logs du pipeline LLM")

# ---------- Utils basiques (sans dépendances externes obligatoires) ----------
def read_events(log_path: str = LOG_FILE, limit: Optional[int] = None) -> List[Dict[str, Any]]:
    """Lit le .jsonl et renvoie une liste d'événements (dict)."""
    p = Path(log_path)
    if not p.exists():
        return []
    evts: List[Dict[str, Any]] = []
    with p.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                evts.append(json.loads(line))
            except Exception:
                continue
    if limit:
        return evts[-limit:]
    return evts

def try_import_pandas():
    try:
        import pandas as pd  # type: ignore
        return pd
    except Exception:
        return None

def to_dataframe(events: List[Dict[str, Any]]):
    """Retourne un DataFrame (si pandas dispo), sinon None."""
    pd = try_import_pandas()
    if pd is None:
        return None
    if not events:
        return pd.DataFrame()
    # aplatissement léger
    rows = []
    for e in events:
        params = e.get("params", {}) or {}
        inp    = e.get("input", {}) or {}
        out    = e.get("output", {}) or {}
        usage  = e.get("usage", {}) or {}
        rows.append({
            "timestamp":  e.get("timestamp") or e.get("ts"),
            "provider":   e.get("provider"),
            "model":      e.get("model"),
            "temperature": params.get("temperature"),
            "max_tokens": params.get("max_tokens"),
            "query":      inp.get("query", ""),
            "context":    inp.get("context", ""),
            "text":       out.get("text", ""),
            "prompt_tokens": usage.get("prompt_tokens"),
            "completion_tokens": usage.get("completion_tokens"),
            "total_tokens": usage.get("total_tokens"),
            "rating":     e.get("rating"),  # -1 / 0 / 1
        })
    df = pd.DataFrame(rows)
    # cast datetime si possible
    if "timestamp" in df.columns:
        try:
            df["timestamp"] = pd.to_datetime(df["timestamp"])
        except Exception:
            pass
    return df

# ---------- Chargement ----------
st.sidebar.header("Fichier")
log_path = st.sidebar.text_input("Chemin du log JSONL", value=str(Path(LOG_FILE).resolve()))
if st.sidebar.button("🔄 Recharger"):
    st.experimental_rerun()

events = read_events(log_path)
st.caption(f"Fichier: `{log_path}` — {len(events)} événements")
if not events:
    st.warning("Aucun événement trouvé. Lance d’abord une génération dans l’app principale.")
    st.stop()

df = to_dataframe(events)
if df is None:
    st.error("`pandas` n'est pas installé. Fais `pip install pandas` pour le tableau et les graphes.")
    st.stop()

# ---------- Filtres ----------
st.sidebar.header("Filtres")
prov_list  = sorted([p for p in df["provider"].dropna().unique().tolist()])
model_list = sorted([m for m in df["model"].dropna().unique().tolist()])
sel_prov   = st.sidebar.multiselect("Provider", prov_list, default=prov_list or None)
sel_model  = st.sidebar.multiselect("Modèle", model_list, default=model_list or None)

# Date range
if "timestamp" in df.columns and df["timestamp"].notna().any():
    min_dt = df["timestamp"].min()
    max_dt = df["timestamp"].max()
    d1, d2 = st.sidebar.date_input(
        "Plage de dates",
        value=(min_dt.date(), max_dt.date())
    )
else:
    d1 = d2 = None

# Rating
rating_map = {"Tous": None, "👍 (+1)": 1, "👎 (-1)": -1, "Sans feedback": "none"}
sel_rating_label = st.sidebar.selectbox("Feedback", list(rating_map.keys()), index=0)
sel_rating = rating_map[sel_rating_label]

# Applique les filtres
mask = df["provider"].isin(sel_prov) if sel_prov else True
df_f = df[mask]
mask = df_f["model"].isin(sel_model) if sel_model else True
df_f = df_f[mask]
if d1 and d2 and "timestamp" in df_f.columns:
    try:
        df_f = df_f[(df_f["timestamp"].dt.date >= d1) & (df_f["timestamp"].dt.date <= d2)]
    except Exception:
        pass
if sel_rating is None:
    pass
elif sel_rating == "none":
    df_f = df_f[df_f["rating"].isna()]
else:
    df_f = df_f[df_f["rating"] == sel_rating]

st.subheader("🧾 Table (filtrée)")
st.dataframe(df_f, use_container_width=True, height=300)

# Exports
c1, c2 = st.columns(2)
with c1:
    st.download_button("⬇️ Export CSV (filtré)", data=df_f.to_csv(index=False).encode("utf-8"),
                       file_name="logs_filtre.csv", mime="text/csv")
with c2:
    st.download_button("⬇️ Export JSON (filtré)", data=df_f.to_json(orient="records", force_ascii=False).encode("utf-8"),
                       file_name="logs_filtre.json", mime="application/json")

st.divider()

# ---------- KPIs ----------
st.subheader("📌 KPIs")
k1, k2, k3, k4 = st.columns(4)
k1.metric("Runs (filtrés)", len(df_f))
k2.metric("Tokens moyens", f"{df_f['total_tokens'].dropna().mean():.1f}" if "total_tokens" in df_f else "—")
k3.metric("👍 positifs", int((df_f["rating"] == 1).sum()) if "rating" in df_f else 0)
k4.metric("👎 négatifs", int((df_f["rating"] == -1).sum()) if "rating" in df_f else 0)

# ---------- Graphiques ----------
pd = try_import_pandas()

if pd is not None and not df_f.empty:
    st.subheader("📈 Évolution des runs")
    if "timestamp" in df_f.columns and df_f["timestamp"].notna().any():
        df_runs = (
            df_f.dropna(subset=["timestamp"])
                .assign(day=lambda x: x["timestamp"].dt.date)
                .groupby("day")["provider"].count()
                .reset_index()
                .rename(columns={"provider": "runs"})
        )
        st.line_chart(df_runs, x="day", y="runs", use_container_width=True)
    else:
        st.info("Pas de colonne `timestamp` exploitable pour la courbe temporelle.")

    if "total_tokens" in df_f.columns:
        st.subheader("📊 Tokens moyens par provider")
        df_tok = (
            df_f.groupby("provider")["total_tokens"]
                .mean()
                .reset_index()
                .rename(columns={"total_tokens": "avg_tokens"})
        )
        st.bar_chart(df_tok, x="provider", y="avg_tokens", use_container_width=True)

    st.subheader("🏷️ Répartition par modèle (compte)")
    df_model = df_f.groupby("model")["query"].count().reset_index().rename(columns={"query": "runs"})
    st.bar_chart(df_model, x="model", y="runs", use_container_width=True)
else:
    st.info("Installe `pandas` pour afficher les graphes.")

st.divider()
st.caption("Astuce : garde ce dashboard ouvert pendant que tu utilises l’app principale, et clique **🔄 Recharger** pour mettre à jour.")