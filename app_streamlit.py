# app_streamlit.py
import streamlit as st
from pipeline import FakeLLM, OllamaLLM, Pipeline, LLMConfig, PipelineInput

st.set_page_config(page_title="Demo Pipeline LLM", page_icon="🧪", layout="wide")
st.title("🧪 Demo Pipeline LLM (fake / Ollama)")

# --- State initial ---
if "query_input" not in st.session_state:
    st.session_state["query_input"] = ""
if "context_input" not in st.session_state:
    st.session_state["context_input"] = ""

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

    # Paramètres Ollama visibles seulement si choisi
    if provider.startswith("Ollama"):
        model_name = st.text_input("Modèle Ollama", value="mistral")
        endpoint   = st.text_input("Endpoint", value="http://localhost:11434/api/generate")
        st.caption("Lance `ollama serve` puis `ollama pull mistral` (une fois).")

# ----- Inputs -----
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

# ----- Run -----
if st.button("▶️ Lancer le pipeline"):
    q = (st.session_state.get("query_input") or "").strip()
    c = (st.session_state.get("context_input") or "").strip()

    if not q and not c:
        st.warning("Ajoute au moins une question ou un contexte.")
    else:
        cfg = LLMConfig(temperature=temperature, max_tokens=max_tokens)
        if provider.startswith("Ollama"):
            llm = OllamaLLM(model=model_name, endpoint=endpoint)
        else:
            llm = FakeLLM(seed=42)

        pipe = Pipeline(cfg=cfg, llm=llm)
        out  = pipe.run(PipelineInput(query=q, context=c))

        st.subheader("Réponse")
        st.write(out.text)

        with st.expander("Usage / Métadonnées"):
            st.json(out.usage)
else:
    st.info("Prépare tes entrées puis clique **Lancer le pipeline**.")
    