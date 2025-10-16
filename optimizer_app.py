# optimizer_app.py
# Lance avec :  python -m streamlit run optimizer_app.py
from __future__ import annotations
import re
import difflib
import streamlit as st
from token_utils import count_tokens, estimate_cost


st.set_page_config(page_title="Token & Prompt Optimizer", page_icon="🪙", layout="wide")
st.title("🪙 Token & Prompt Optimizer")

# --------------------------
# Règles d’optimisation
# --------------------------
POLITESSE_PATTERNS = [
    r"\b(?:s'il te plaît|s'il vous plaît|svp)\b",
    r"\b(?:merci d'avance|merci beaucoup|merci)\b",
    r"\b(?:bonjour|bonsoir|hello|salut)\b",
    r"\b(?:peux-tu|pourrais-tu|pourriez-vous|si possible)\b",
    r"\b(?:j'aimerais|je souhaiterais|serait-il possible de)\b",
]
FILLER_PATTERNS = [
    r"\b(?:de manière|d'une manière|dans le cadre de|afin de|veuillez)\b",
    r"\b(?:le cas échéant|si besoin|au besoin)\b",
]


def clean_politesse(text: str) -> tuple[str, list[str]]:
    tips: list[str] = []
    out = text
    for pat in POLITESSE_PATTERNS:
        new = re.sub(pat, "", out, flags=re.IGNORECASE)
        if new != out:
            tips.append("Suppression de formules de politesse/rituels.")
            out = new

    for pat in FILLER_PATTERNS:
        new = re.sub(pat, "", out, flags=re.IGNORECASE)
        if new != out:
            tips.append("Suppression de tournures verbeuses (filler).")
            out = new

    # espaces multiples -> un espace
    new = re.sub(r"[ \t]{2,}", " ", out)
    if new != out:
        out = new

    # lignes multiples vides -> une
    out = re.sub(r"\n{3,}", "\n\n", out)
    return out.strip(), tips


def tighten_instructions(text: str) -> tuple[str, list[str]]:
    """
    Convertit phrases longues en puces structurées quand pertinent.
    Tente d’extraire des consignes -> listes.
    """
    tips: list[str] = []
    lines = [l.strip() for l in text.strip().splitlines() if l.strip()]
    if len(lines) <= 1:  # pas de multi-ligne -> retour direct
        return text.strip(), tips

    # Heuristique : si >2 lignes non listées, on crée des puces
    if sum(1 for l in lines if not l.startswith(("-", "•", "*", "—"))) >= 2:
        tips.append("Structuration en puces pour réduire l’ambiguïté.")
        bullets = []
        for l in lines:
            bullets.append(f"- {l}")
        return "\n".join(bullets), tips

    return text, tips


def add_output_constraints(text: str) -> tuple[str, list[str]]:
    """
    Ajoute une contrainte de format court si aucune n’existe (limiter les tokens de sortie).
    """
    tips: list[str] = []
    has_len = bool(re.search(r"\b(\d+)\s*(?:mots|phrases|points)\b", text, re.IGNORECASE))
    has_json = "```json" in text.lower() or "format:" in text.lower()
    if not has_len and not has_json:
        tips.append("Ajout d’une limite de longueur (réponse concise).")
        text += "\n\nContrainte : réponds en 5 points concis (max 120 mots)."
    return text, tips


def introduce_variables(text: str) -> tuple[str, list[str]]:
    """
    Suggère l’introduction de variables {lang}, {style}, {n} si mots-clés présents.
    """
    tips: list[str] = []
    t = text
    if re.search(r"\b(tradui[st]|anglais|français|espagnol|german|allemand)\b", t, re.IGNORECASE):
        if "{lang}" not in t:
            t += "\nParamètres : {lang=fr|en|es|de}"
            tips.append("Paramétrisation de la langue via {lang}.")
    if re.search(r"\b(résume|résumé|summary)\b", t, re.IGNORECASE) and "{n}" not in t:
        t += "\nParamètres : {n=2}  # nombre de phrases/points"
        tips.append("Paramétrisation du nombre de phrases {n}.")
    return t, tips


def optimize_prompt(raw: str) -> tuple[str, list[str]]:
    """
    Applique une série d’optimisations simples (non sémantiques).
    Retourne : prompt_optimisé, [liste de conseils appliqués]
    """
    tips_all: list[str] = []
    cur = raw.strip()

    cur, tips = clean_politesse(cur)
    tips_all += tips

    cur, tips = tighten_instructions(cur)
    tips_all += tips

    cur, tips = add_output_constraints(cur)
    tips_all += tips

    cur, tips = introduce_variables(cur)
    tips_all += tips

    # Nettoyage final espaces
    cur = re.sub(r"[ \t]{2,}", " ", cur).strip()
    return cur, tips_all


# --------------------------
# UI
# --------------------------
c_left, c_right = st.columns([1, 1])

with c_left:
    st.subheader("🎯 Prompt d’entrée")
    prompt = st.text_area(
        "Colle ici ton prompt (avant optimisation)",
        height=220,
        placeholder="Ex. Bonjour, peux-tu s'il te plaît résumer ce texte...",
    )

    st.caption("Optionnel : quelques paramètres pour l’estimation des coûts")
    model_hint = st.text_input("Modèle (hint pour le comptage de tokens)", value="mistral")
    exp_out_tokens = st.slider("Sortie attendue (tokens)", min_value=0, max_value=2000, value=250, step=10)

    st.markdown("**Tarifs / 1K tokens** (laisse à 0 si tu veux juste comparer les tokens)")
    c1, c2 = st.columns(2)
    with c1:
        price_in = st.number_input("Entrée (prompt)", min_value=0.0, value=0.0, step=0.001, format="%.4f")
    with c2:
        price_out = st.number_input("Sortie (completion)", min_value=0.0, value=0.0, step=0.001, format="%.4f")

    run = st.button("🚀 Optimiser et estimer")

with c_right:
    st.subheader("✨ Prompt optimisé")
    if run and prompt.strip():
        # Avant
        in_tokens_before = count_tokens(prompt, model_hint=model_hint)
        cost_before = estimate_cost(in_tokens_before, exp_out_tokens, price_in, price_out)

        # Optimisation
        optimized, tips = optimize_prompt(prompt)

        # Après
        in_tokens_after = count_tokens(optimized, model_hint=model_hint)
        cost_after = estimate_cost(in_tokens_after, exp_out_tokens, price_in, price_out)

        # Affichage résultats
        st.text_area("Version optimisée", value=optimized, height=220)

        # Stats
        st.markdown("### 📊 Statistiques")
        colA, colB, colC = st.columns(3)
        with colA:
            st.metric("Tokens (entrée) AVANT", in_tokens_before)
        with colB:
            st.metric("Tokens (entrée) APRÈS", in_tokens_after, delta=in_tokens_after - in_tokens_before)
        with colC:
            gain = in_tokens_before - in_tokens_after
            st.metric("Gain tokens (entrée)", gain)

        st.markdown("### 💰 Estimation des coûts")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Coût AVANT", f"{cost_before:.4f}")
        with col2:
            st.metric("Coût APRÈS", f"{cost_after:.4f}", delta=cost_after - cost_before)
        with col3:
            st.metric("Économie (estim.)", f"{(cost_before - cost_after):.4f}")

        # Conseils appliqués
        if tips:
            st.markdown("### ✅ Optimisations appliquées")
            for t in sorted(set(tips)):
                st.write(f"- {t}")

        # Diff (visuel brut)
        st.markdown("### 🔍 Diff (brut)")
        diff = difflib.unified_diff(
            prompt.splitlines(),
            optimized.splitlines(),
            lineterm="",
            fromfile="prompt_avant",
            tofile="prompt_apres",
        )
        st.code("\n".join(diff) or "(Aucune différence détectée)")

        # Téléchargement
        st.download_button(
            "⬇️ Télécharger le prompt optimisé",
            data=optimized.encode("utf-8"),
            file_name="prompt_optimise.txt",
            mime="text/plain",
        )

    else:
        st.info("Colle un prompt à gauche puis clique **Optimiser et estimer**.")
        