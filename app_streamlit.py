# app_streamlit.py — version clean & robuste
import os, sys
from pathlib import Path
import streamlit as st

# -----------------------------------------------------------------------------
# Imports pipeline
# -----------------------------------------------------------------------------
from pipeline import FakeLLM, OllamaLLM, Pipeline, LLMConfig, PipelineInput

# -----------------------------------------------------------------------------
# Imports prompts & guards
# -----------------------------------------------------------------------------
from prompts.templates import SUMMARY_TEMPLATE, QA_TEMPLATE, render_template
try:
    from prompts.templates_extra import TRANSLATION_TEMPLATE, EXPLAIN_TEMPLATE, SIMPLIFY_TEMPLATE
except Exception:
    TRANSLATION_TEMPLATE = EXPLAIN_TEMPLATE = SIMPLIFY_TEMPLATE = None
from prompts.guards import enforce_limits

# -----------------------------------------------------------------------------
# Imports evaluation (logger + métriques)
# -----------------------------------------------------------------------------
try:
    from evaluation import (
        LOG_FILE, log_event, read_events, to_dataframe,
        basic_kpis, tokens_by_provider, runs_over_time,
    )
except Exception:
    PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
    if PROJECT_ROOT not in sys.path:
        sys.path.insert(0, PROJECT_ROOT)
    from evaluation.logger import LOG_FILE, log_event, read_events, to_dataframe
    try:
        from evaluation.metrics import basic_kpis, tokens_by_provider, runs_over_time
    except Exception:
        basic_kpis = tokens_by_provider = runs_over_time = None

# -----------------------------------------------------------------------------
# Helpers UI
# -----------------------------------------------------------------------------
def badge(text, color="#2563eb"):
    st.markdown(
        f"<span style='display:inline-block;padding:4px 10px;border-radius:999px;"
        f"background:{color};color:white;font-weight:600;font-size:12px'>{text}</span>",
        unsafe_allow_html=True,
    )

@st.cache_data(ttl=10.0)
def cached_read_events(path: str):
    return read_events(log_path=path)

# -----------------------------------------------------------------------------
# UI de base
# -----------------------------------------------------------------------------
st.set_page_config(page_title="Demo Pipeline LLM", page_icon="🧪", layout="wide")
st.title("🧪 Demo Pipeline LLM (fake / Ollama)")

# State initial
st.session_state.setdefault("query_input", "")
st.session_state.setdefault("context_input", "")
st.session_state.setdefault("last_run", None)

# ----- Sidebar -----
with st.sidebar:
    st.header("Moteur")
    provider = st.radio(
        "Choix du provider",
        ["FakeLLM (mock)", "Ollama (local)"],
        index=0,
        help="FakeLLM = pas d'appel réseau. Ollama = http://localhost:11434."
    )

    st.header("Paramètres LLM")
    temperature = st.slider("Temperature", 0.0, 1.0, 0.2, 0.1)
    max_tokens  = st.slider("Max tokens", 32, 1024, 300, 16)

    # ---- Traduction : langue cible
    target_lang = st.selectbox(
        "Langue cible (traduction)",
        ["anglais", "français", "espagnol", "allemand", "italien", "portugais"],
        index=0,
        help="Utilisée quand le prompt contient 'traduis' / 'traduire'."
    )

    # (placeholder pour plus tard si tu veux du streaming)
    stream_mode = st.checkbox(
        "Afficher en streaming", value=False,
        help="Affiche la réponse au fil de l'eau si le provider le permet."
    )

    model_name = endpoint = None
    if provider.startswith("Ollama"):
        model_name = st.text_input("Modèle Ollama", value="mistral")
        endpoint   = st.text_input("Endpoint", value="http://localhost:11434/api/generate")
        st.caption("Lance `ollama serve` puis `ollama pull mistral` (une fois).")

# ----- Entrées -----
st.subheader("Entrées")
c1, c2 = st.columns(2)
with c1:
    st.text_area("Question / Instruction", height=140, key="query_input", placeholder="Ex: Résume ce texte…")
with c2:
    st.text_area("Contexte (optionnel)", height=140, key="context_input", placeholder="Colle un texte ici…")

def remplir_exemple():
    st.session_state["query_input"] = "Résume ce texte en 2 phrases."
    st.session_state["context_input"] = (
        "Les pollinisateurs dépendent d'une ressource étalée toute l'année. "
        "Un jardin mellifère combine arbustes d'hiver (mahonia, laurier-tin) "
        "et vivaces d'été (lavande, sauge), puis asters d'automne. "
        "L'exposition et le sol influencent la durée de floraison."
    )
st.button("Remplir un exemple", on_click=remplir_exemple)

st.divider()

# -----------------------------------------------------------------------------
# RUN — tout est encapsulé dans le bouton
# -----------------------------------------------------------------------------
if st.button("▶️ Lancer le pipeline"):
    q = (st.session_state.get("query_input") or "").strip()
    c = (st.session_state.get("context_input") or "").strip()

    if not q and not c:
        st.warning("Ajoute au moins une question ou un contexte.")
    else:
        # 1) Config + provider
        cfg = LLMConfig(temperature=temperature, max_tokens=max_tokens)
        if provider.startswith("Ollama"):
            if OllamaLLM is None:
                st.error("OllamaLLM indisponible (module non installé ou import échoué).")
                st.stop()
            llm = OllamaLLM(model=model_name, endpoint=endpoint)
        else:
            llm = FakeLLM(seed=42)

        pipe = Pipeline(cfg=cfg, llm=llm)

        # 2) Détection d'intention (mode)
        q_low = q.lower()
        is_summary     = "résume" in q_low
        is_translation = ("traduis" in q_low) or ("traduire" in q_low)
        is_explain     = ("explique" in q_low) or ("expliquer" in q_low)
        is_simplify    = any(k in q_low for k in ["simplifie", "rends plus simple", "clarifie"])

        # 3) Template + rendu
        if is_summary and SUMMARY_TEMPLATE:
            rendered = render_template(SUMMARY_TEMPLATE, n_sentences=2, context=c or q)
            mode = "Résumé"
        elif is_translation and TRANSLATION_TEMPLATE:
            rendered = render_template(
                TRANSLATION_TEMPLATE,
                target_lang=target_lang,
                text=c or q
            )
            mode = f"Traduction → {target_lang}"
        elif is_explain and EXPLAIN_TEMPLATE:
            rendered = render_template(EXPLAIN_TEMPLATE, topic=q)
            mode = "Explication"
        elif is_simplify and SIMPLIFY_TEMPLATE:
            rendered = render_template(SIMPLIFY_TEMPLATE, text=c or q)
            mode = "Simplification"
        else:
            rendered = render_template(QA_TEMPLATE, question=q, context=c)
            mode = "QA"

        # 4) Guardrails (taille + nettoyage)
        user_payload, was_cut = enforce_limits(rendered["user"])
        prompt = f"{rendered['system']}\n\n{user_payload}"

        # 5) Exécution pipeline
        out = pipe.run(PipelineInput(query=prompt, context=""))

        # 6) Log + sauvegarde
        payload = {
            "mode": mode,
            "provider": "Ollama" if provider.startswith("Ollama") else "FakeLLM",
            "model": (model_name if provider.startswith("Ollama") else "fake-llm"),
            "params": {"temperature": temperature, "max_tokens": max_tokens},
            "input": {"query": q, "context": c},
            "output": {"text": out.text},
            "usage": out.usage,
        }
        try:
            log_event(payload)
        except Exception as e:
            st.warning(f"Log non enregistré : {e}")

        st.session_state["last_run"] = payload

# -----------------------------------------------------------------------------
# Affichage unique + feedback (si une génération existe)
# -----------------------------------------------------------------------------
last = st.session_state.get("last_run")
if last:
    mode_color = {
        "QA": "#2563eb", "Résumé": "#16a34a", "Traduction": "#9333ea",
        "Explication": "#ea580c", "Simplification": "#0ea5e9"
    }
    badge(f"Mode : {last.get('mode','QA')}", mode_color.get(last.get('mode','QA'), "#2563eb"))

    st.subheader("Réponse")
    st.write(last["output"]["text"])

    fb_cols = st.columns(3)
    with fb_cols[0]:
        if st.button("👍 Utile"):
            try:
                log_event(last, rating=1)
                st.success("Merci pour le feedback (👍).")
            except Exception as e:
                st.warning(f"Feedback non enregistré : {e}")
    with fb_cols[1]:
        if st.button("👎 Pas utile"):
            try:
                log_event(last, rating=-1)
                st.info("Feedback reçu (👎).")
            except Exception as e:
                st.warning(f"Feedback non enregistré : {e}")
    with fb_cols[2]:
        st.caption("Ton feedback nous aide à mesurer la qualité.")

    with st.expander("Usage / Métadonnées"):
        st.json(last.get("usage") or {})
else:
    st.info("Aucune réponse encore. Lance une génération.")

st.divider()

# -----------------------------------------------------------------------------
# Historique / KPIs
# -----------------------------------------------------------------------------
with st.expander("📊 Historique des exécutions", expanded=False):
    events = cached_read_events(LOG_FILE)
    if not events:
        st.info("Aucun log pour l’instant. Lance une génération pour créer le premier.")
    else:
        if basic_kpis is not None:
            kpis = basic_kpis(events)
            k1, k2, k3, k4 = st.columns(4)
            k1.metric("Runs", kpis["runs"])
            k2.metric("Tokens moyens (total)", kpis["avg_tokens"]["total"])
            k3.metric("👍 Positifs", kpis["feedback"]["positive"])
            k4.metric("👎 Négatifs", kpis["feedback"]["negative"])
            st.write("Par provider :", kpis["providers"])
            st.write("Par modèle :", kpis["models"])
        else:
            st.caption("Installe/active evaluation.metrics pour voir les KPIs.")

        df = to_dataframe(events)
        if df is not None:
            st.dataframe(df, use_container_width=True)
            try:
                import pandas as pd  # noqa
                if tokens_by_provider is not None:
                    rows = tokens_by_provider(events)
                    if rows:
                        st.subheader("📊 Tokens moyens par provider")
                        st.bar_chart(pd.DataFrame(rows), x="provider", y="avg_tokens", use_container_width=True)
                if runs_over_time is not None:
                    rows_t = runs_over_time(events, bucket="day")
                    if rows_t:
                        st.subheader("📈 Runs par jour")
                        st.line_chart(pd.DataFrame(rows_t), x="date", y="runs", use_container_width=True)
            except Exception:
                pass

            import json
            st.download_button("⬇️ Export JSONL", data=open(LOG_FILE, "rb").read(),
                               file_name="log.jsonl", mime="application/json")
            st.download_button("⬇️ Export CSV", data=df.to_csv(index=False).encode("utf-8"),
                               file_name="log.csv", mime="text/csv")
        else:
            import json
            st.code("\n".join([json.dumps(e, ensure_ascii=False) for e in events][:50]), language="json")
            st.caption("Installe `pandas` pour le tableau (pip install pandas).")

# ----- Infos fichier de log -----
log_path = Path(LOG_FILE).resolve()
st.divider()
st.subheader("📁 Fichier de log")
st.code(str(log_path), language="text")
if log_path.exists():
    try:
        size = log_path.stat().st_size
        with log_path.open("r", encoding="utf-8") as f:
            n_lines = sum(1 for _ in f)
        st.success(f"Le fichier existe — ~{size} octets, {n_lines} événements.")
    except Exception as e:
        st.warning(f"Impossible de lire le fichier de log : {e}")
else:
    st.info("Le fichier n’existe pas encore. Lance une génération pour créer le premier log.")