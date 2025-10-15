# app_streamlit.py
import streamlit as st
from pipeline import FakeLLM, Pipeline, LLMConfig, PipelineInput

st.set_page_config(page_title="Demo Pipeline LLM (fake)", page_icon="🧪", layout="centered")
st.title("🧪 Demo Pipeline LLM (fake)")

# --- Initialisation de l'état (avant tout widget) ---
if "query_input" not in st.session_state:
    st.session_state["query_input"] = ""
if "context_input" not in st.session_state:
    st.session_state["context_input"] = ""

# ----- Sidebar: paramètres LLM -----
with st.sidebar:
    st.header("Paramètres LLM")
    temperature = st.slider("Temperature", 0.0, 1.0, 0.2, 0.1)
    max_tokens  = st.slider("Max tokens", 32, 1024, 300, 16)
    st.caption("Cette démo utilise un **FakeLLM** local (aucun appel d’API).")

# ----- Callback bouton exemple (défini AVANT les widgets) -----
def remplir_exemple():
    st.session_state["query_input"] = "Résume ce texte en 2 phrases."
    st.session_state["context_input"] = (
        "Les pollinisateurs dépendent d'une ressource étalée toute l'année. "
        "Un jardin mellifère combine arbustes d'hiver (mahonia, laurier-tin) "
        "et vivaces d'été (lavande, sauge), puis asters d'automne. "
        "L'exposition et le sol influencent la durée de floraison."
    )

# ----- Entrées -----
st.subheader("Entrées")
c1, c2 = st.columns(2)

with c1:
    query = st.text_area(
        "Question / Instruction",
        height=140,
        key="query_input",
        placeholder="Ex: Résume ce texte…"
    )

with c2:
    context = st.text_area(
        "Contexte (optionnel)",
        height=140,
        key="context_input",
        placeholder="Colle un texte ici…"
    )

ex_col1, ex_col2 = st.columns([1, 2])

with ex_col1:
    st.button("Remplir un exemple", on_click=remplir_exemple, key="fill_example_btn")

with ex_col2:
    st.caption("Astuce : mets le mot **“résume”** pour déclencher le mode résumé de la démo.")

st.divider()

# ----- Exécuter le pipeline -----
if st.button("▶️ Lancer le pipeline", key="run_btn"):
    q = (st.session_state.get("query_input") or "").strip()
    c = (st.session_state.get("context_input") or "").strip()

    if not q and not c:
        st.warning("Ajoute au moins une question ou un contexte.")
    else:
        cfg  = LLMConfig(temperature=temperature, max_tokens=max_tokens)
        pipe = Pipeline(cfg=cfg)               # le Pipeline instancie FakeLLM en interne
        out  = pipe.run(PipelineInput(query=q, context=c))

        st.subheader("Réponse")
        st.write(out.text)                     # IMPORTANT : .text

        with st.expander("Usage / Métadonnées"):
            st.json(out.usage)                 # IMPORTANT : .usage
else:
    st.info("Prépare tes entrées puis clique **Lancer le pipeline**.")
    