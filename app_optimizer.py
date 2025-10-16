# app_optimizer.py — Optimiseur de prompt (UX simple, hors-ligne)
import os
import streamlit as st
from pathlib import Path

from utils.token_utils import (
    estimate_pair, estimate_tokens, optimize_prompt,
    wrap_as_structured_instruction, MODEL_PROFILES, DEFAULT_MODEL
)

st.set_page_config(page_title="Prompt Optimizer", page_icon="🧹", layout="wide")
st.title("🧹 Optimiseur de prompt (tokens & clarté)")

# — Thème léger (compatible avec ton app principale)
st.markdown("""
<style>
h1, h2, h3 { color: #a3e635; }
.stButton>button { background:#22c55e;color:white;border:none;border-radius:8px;padding:.5rem 1rem; }
.stButton>button:hover { background:#16a34a; }
</style>
""", unsafe_allow_html=True)

# — State
st.session_state.setdefault("prompt_raw", "")
st.session_state.setdefault("context_raw", "")
st.session_state.setdefault("optimized", "")

# — Sidebar
with st.sidebar:
    st.header("Paramètres")
    model = st.selectbox("Modèle (profil d’estimation)", list(MODEL_PROFILES.keys()), index=0)
    budget = st.slider("Budget max tokens (objectif)", min_value=64, max_value=4096, value=512, step=32)
    add_struct = st.checkbox("Structurer en JSON (optionnel)")

# — Inputs
c1, c2 = st.columns(2)
with c1:
    st.subheader("Prompt")
    prompt = st.text_area("Texte à optimiser", key="prompt_raw", height=220, placeholder="Colle ici ton prompt…")
with c2:
    st.subheader("Contexte (optionnel)")
    context = st.text_area("Contexte", key="context_raw", height=220, placeholder="Contexte, données, exemple…")

# — Analyse
if st.button("🔍 Analyser"):
    est = estimate_pair(prompt, context, model=model)
    st.success(f"Estimation tokens — prompt: {est['prompt']} | contexte: {est['context']} | total: {est['total']}")
    if est["total"] > budget:
        st.warning(f"Tu dépasses le budget ({est['total']} > {budget}). Clique **Optimiser** pour réduire.")

# — Optimisation
if st.button("🧹 Optimiser"):
    base = prompt.strip()
    if add_struct and base:
        base = wrap_as_structured_instruction(base)
    optimized, stats = optimize_prompt(base)
    st.session_state["optimized"] = optimized

    # Résultats
    before = estimate_pair(prompt, context, model=model)["total"]
    after  = estimate_pair(optimized, context, model=model)["total"]

    st.subheader("Résultat")
    colA, colB, colC = st.columns(3)
    colA.metric("Chars économisés", stats["chars_saved"])
    colB.metric("Réduction (%)", f"{stats['pct_saved']}%")
    colC.metric("Tokens estimés", f"{after} (avant: {before})")

    st.markdown("**Prompt optimisé :**")
    st.text_area("Copier-coller", value=optimized, height=220, key="optimized_view")

    # Téléchargement
    st.download_button(
        "⬇️ Télécharger (optimized_prompt.txt)",
        data=optimized.encode("utf-8"),
        file_name="optimized_prompt.txt",
        mime="text/plain"
    )

st.divider()
st.caption("ℹ️ Estimation simple (1 token ≈ 4 caractères). Aucune requête réseau, aucun coût.")
