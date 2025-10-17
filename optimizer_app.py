# app_optimizer.py
import streamlit as st

from pipeline import FakeLLM, OllamaLLM, LLMConfig, PipelineInput, Pipeline
from prompts.optimizer_smart import smart_optimize_prompt, estimate_tokens

st.set_page_config(page_title="Token & Prompt Optimizer", page_icon="🧮", layout="wide")
st.title("🧮 Token & Prompt Optimizer")

# --- Entrées ---
c1, c2 = st.columns(2)
with c1:
    st.subheader("🎯 Prompt d’entrée")
    raw = st.text_area("Colle ici ton prompt (avant optimisation)", height=220, placeholder="Ton prompt…")

with c2:
    st.subheader("✨ Prompt optimisé")
    optimized_box = st.empty()  # on remplira après clic

st.divider()

# Paramètres
with st.sidebar:
    st.header("Paramètres")
    mode_intelligent = st.toggle("Activer l’optimisation intelligente (Ollama)", value=True,
                                 help="Réécriture par LLM (Mistral via Ollama). Sinon, mode mécanique.")
    target_tokens = st.slider("Cible (tokens entrée)", 32, 512, 128, 16)
    max_words     = st.slider("Contrainte max mots (hint)", 30, 300, 120, 10)
    temperature   = st.slider("Température LLM", 0.0, 1.0, 0.2, 0.1)

    # Config Ollama
    model_name = st.text_input("Modèle Ollama", "mistral")
    endpoint   = st.text_input("Endpoint", "http://localhost:11434/api/generate")
    st.caption("Démarre `ollama serve` et `ollama pull mistral` si besoin.")

# Bouton
if st.button("🚀 Optimiser"):
    if not raw.strip():
        st.warning("Ajoute un prompt.")
        st.stop()

    if mode_intelligent:
        try:
            llm = OllamaLLM(model=model_name, endpoint=endpoint)
            res = smart_optimize_prompt(
                llm=llm,
                raw_prompt=raw,
                target_tokens=target_tokens,
                max_words=max_words,
                temperature=temperature,
                max_tokens=256,
            )
            optimized_box.text_area("Version optimisée", res.optimized, height=220)
            st.subheader("📊 Statistiques")
            c3, c4, c5 = st.columns(3)
            c3.metric("Tokens (entrée) AVANT", res.tokens_in)
            c4.metric("Tokens (entrée) APRÈS",  res.tokens_out, delta=-res.gain_tokens if res.gain_tokens>0 else res.tokens_out - res.tokens_in)
            c5.metric("Gain tokens (entrée)",   res.gain_tokens)

        except Exception as e:
            st.error(f"Échec de l’optimisation intelligente : {e}")
    else:
        # Fallback Mécanique minimal : nettoie politesse + ajoute contrainte
        import re
        prompt = raw.strip()
        # Supprime salutations courantes
        prompt = re.sub(r"(?i)\b(bonjour|salut|merci|s'il te plaît|svp|stp)\b[:,\s]*", "", prompt)
        prompt = prompt.strip()
        # Ajoute contrainte de concision (si pas déjà là)
        if "réponds en" not in prompt.lower():
            prompt += f"\n\nContrainte : réponds en points concis (≤ {max_words} mots)."
        optimized_box.text_area("Version optimisée", prompt, height=220)

        t_in  = estimate_tokens(raw)
        t_out = estimate_tokens(prompt)
        st.subheader("📊 Statistiques")
        c3, c4, c5 = st.columns(3)
        c3.metric("Tokens (entrée) AVANT", t_in)
        c4.metric("Tokens (entrée) APRÈS", t_out, delta=t_out - t_in)
        c5.metric("Gain tokens (entrée)", t_in - t_out)

st.info("Astuce : colle d’abord ton prompt ici pour le réduire, puis utilise-le dans l’app principale.")