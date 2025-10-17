# app_optimizer.py — BotanAI Optimizer v2.3
from pathlib import Path
import streamlit as st
from utils.prefs import load_prefs, save_prefs
from utils.token_utils import MODEL_PROFILES, estimate_tokens, optimize_prompt
import difflib, pandas as pd

# -------------------- Page config --------------------
st.set_page_config(page_title="BotanAI Optimizer v2.3", page_icon="🌿", layout="wide")

# Charger préférences utilisateur
_prefs = load_prefs()
for k, v in _prefs.items():
    st.session_state.setdefault(k, v)

# -------------------- Thèmes CSS --------------------
LIGHT_VARS = """
:root{
  --bg:#f7fbfc; --card:#ffffff; --ink:#0f172a;
  --accent:#1e90ff; --accent-2:#10b981; --muted:#64748b;
  --border:#e6eef5;
}
"""
DARK_VARS = """
:root{
  --bg:#0b1220; --card:#0f172a; --ink:#e5f0ff;
  --accent:#60a5ff; --accent-2:#34d399; --muted:#93a4bd;
  --border:#1f2a44;
}
"""
BASE_CSS = """
html,body,section.main{background:var(--bg);}
.block-container{max-width:980px;padding-top:0.6rem;}
h1,h2,h3{color:var(--accent-2);margin:0.3rem 0 0.6rem 0;}
.small{font-size:0.9rem;color:var(--muted);}
.stTextArea textarea{min-height:120px !important;}
.card{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:12px;}
.kpi{display:flex;gap:12px}
.kpi .box{flex:1;background:var(--card);border:1px solid var(--border);border-radius:12px;padding:10px 12px}
.kpi .label{color:var(--muted);font-size:.85rem;margin-bottom:4px}
.kpi .value{font-weight:700;color:var(--ink)}
.kpi .delta{font-size:.85rem;color:#ef4444}
.kpi .delta.pos{color:#16a34a}
.diff span[del]{background:#ffe2e2;text-decoration:line-through;color:#7f1d1d;padding:0 .15rem;border-radius:3px}
.diff span[add]{background:#d1fae5;color:#065f46;padding:0 .15rem;border-radius:3px}
.stButton>button{background:var(--accent);border:none;color:white;border-radius:10px;padding:.5rem .9rem}
.stButton>button:hover{filter:brightness(0.95)}
"""

def inject_theme(choice: str):
    if choice == "Sombre":
        st.markdown(f"<style>{DARK_VARS}{BASE_CSS}</style>", unsafe_allow_html=True)
    elif choice == "Clair":
        st.markdown(f"<style>{LIGHT_VARS}{BASE_CSS}</style>", unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <style>
        @media (prefers-color-scheme: dark) {{{DARK_VARS}{BASE_CSS}}}
        @media (prefers-color-scheme: light) {{{LIGHT_VARS}{BASE_CSS}}}
        </style>
        """, unsafe_allow_html=True)

# injection du thème initial
inject_theme(st.session_state.get("theme_choice", "Auto"))

# contraste sombre
st.markdown("""
<style>
@media (prefers-color-scheme: dark){
  .stTextArea textarea{background:#0f172a !important;color:#e5f0ff !important;}
  .card,.kpi .box{background:#0f172a !important;border-color:#1f2a44 !important;}
  .kpi .value{color:#e5f0ff !important;}
  .small{color:#93a4bd !important;}
}
div[data-testid="stSlider"] div[role="slider"][aria-disabled="true"]{filter:grayscale(1) opacity(0.6);}
</style>
""", unsafe_allow_html=True)

# -------------------- Coût + Diff utils --------------------
RATES = {
    "mistral": {"prompt":0.002,"completion":0.002},
    "llama3": {"prompt":0.0005,"completion":0.0005},
    "gpt-4o-mini": {"prompt":0.005,"completion":0.015},
}
def estimate_cost(tp, tc, model):
    r = RATES.get(model, RATES["gpt-4o-mini"])
    return round((tp*r["prompt"] + tc*r["completion"]) / 1000.0, 6)
def ndiff_html(before, after):
    out=[]
    for tok in difflib.ndiff(before.split(), after.split()):
        if tok.startswith("- "): out.append(f"<span del>{tok[2:]}</span>")
        elif tok.startswith("+ "): out.append(f"<span add>{tok[2:]}</span>")
        elif tok.startswith("? "): continue
        else: out.append(tok[2:] if tok.startswith("  ") else tok)
    return " ".join(out)

# -------------------- UI principale --------------------
st.title("🌿 BotanAI Optimizer v2.3")
st.caption("Optimise les prompts, réduit les tokens et estime le coût. Version compacte, multithème et hors-ligne.")

# ───── SIDEBAR ─────
with st.sidebar:
    st.header("Paramètres")

    # Thème
    theme_choice = st.radio(
        "Thème", ["Auto","Clair","Sombre"],
        index=["Auto","Clair","Sombre"].index(st.session_state["theme_choice"]),
        horizontal=True, key="theme_choice",
        on_change=lambda:(inject_theme(st.session_state["theme_choice"]),save_prefs({**st.session_state}))
    )

    model = st.selectbox(
        "Modèle (profil d’estimation)", list(MODEL_PROFILES.keys()),
        index=list(MODEL_PROFILES.keys()).index(st.session_state["model"]),
        key="model", on_change=lambda:save_prefs({**st.session_state})
    )

    budget_on = st.checkbox("Imposer un budget de tokens",value=st.session_state["budget_on"],key="budget_on",on_change=lambda:save_prefs({**st.session_state}))
    budget = st.slider("Budget (tokens max)",20,2000,st.session_state["budget"],10,key="budget",disabled=not budget_on,on_change=lambda:save_prefs({**st.session_state}))

    aggressive = st.checkbox("Mode agressif",value=st.session_state["aggressive"],help="Coupe bonjour/merci/etc. + serrage supplémentaire.",key="aggressive",on_change=lambda:save_prefs({**st.session_state}))

    st.markdown("---")
    add_constraint = st.checkbox("Contraintes automatiques",value=st.session_state["add_constraint"],key="add_constraint",on_change=lambda:save_prefs({**st.session_state}))
    lite_spell = st.checkbox("Correction légère (typos courantes)",value=st.session_state["lite_spell"],key="lite_spell",on_change=lambda:save_prefs({**st.session_state}))
    n_points = st.slider("Nb points",3,10,st.session_state["n_points"],key="n_points",disabled=not add_constraint,on_change=lambda:save_prefs({**st.session_state}))
    max_words = st.slider("Max mots",60,200,st.session_state["max_words"],10,key="max_words",disabled=not add_constraint,on_change=lambda:save_prefs({**st.session_state}))

    st.markdown("**Presets rapides**")
    c1,c2,c3=st.columns(3)
    with c1:
        if st.button("🎯\n3/80",use_container_width=True): st.session_state.update({"n_points":3,"max_words":80}); save_prefs({**st.session_state})
    with c2:
        if st.button("🧭\n5/120",use_container_width=True): st.session_state.update({"n_points":5,"max_words":120}); save_prefs({**st.session_state})
    with c3:
        if st.button("📦\n7/150",use_container_width=True): st.session_state.update({"n_points":7,"max_words":150}); save_prefs({**st.session_state})

# ───── CONTENU ─────
ultra_compact = st.checkbox("Mode compact ++",value=st.session_state["ultra_compact"],key="ultra_compact",on_change=lambda:save_prefs({**st.session_state}))
if ultra_compact:
    st.markdown("<style>.block-container{max-width:860px;padding-top:.3rem}.stTextArea textarea{min-height:100px !important}.card,.kpi .box{padding:8px 10px;border-radius:10px}</style>",unsafe_allow_html=True)

# zone de saisie avec compteur live
st.session_state.setdefault("base_prompt","")
def _on_base_change():
    st.session_state["tokens_before"]=estimate_tokens(st.session_state["base_prompt"],st.session_state["model"])
st.subheader("Prompt d’entrée")
st.text_area(" ",key="base_prompt",height=140,placeholder="Colle ici un prompt…",on_change=_on_base_change)
tokens_before=st.session_state.get("tokens_before",0)

colA,colB,colC=st.columns(3)
with colA: st.markdown(f"<div class='card'><div class='small'>Modèle</div><b>{st.session_state['model']}</b></div>",unsafe_allow_html=True)
with colB: st.markdown(f"<div class='card'><div class='small'>Tokens (avant)</div><b>{tokens_before}</b></div>",unsafe_allow_html=True)
with colC: st.markdown(f"<div class='card'><div class='small'>Budget</div><b>{st.session_state['budget'] if st.session_state['budget_on'] else '—'}</b></div>",unsafe_allow_html=True)

st.markdown("<div class='small'></div>",unsafe_allow_html=True)

# ───── ACTION : Optimiser ─────
if st.button("🚀 Optimiser"):
    base=(st.session_state["base_prompt"] or "").strip()
    if not base:
        st.warning("Ajoute un prompt pour commencer.")
    else:
        opt,stats=optimize_prompt(
            base,
            model=st.session_state["model"],
            budget_tokens=st.session_state["budget"] if st.session_state["budget_on"] else None,
            aggressive=st.session_state["aggressive"],
            lite_spell=st.session_state["lite_spell"],
        )
        if st.session_state["add_constraint"]:
            opt += f"\n\nContraintes : réponds en {st.session_state['n_points']} points concis (max {st.session_state['max_words']} mots)."

        # KPIs
        k1,k2,k3,k4=st.columns(4)
        k1.markdown(f"<div class='box'><div class='label'>Chars →</div><div class='value'>{stats['chars_before']} → {stats['chars_after']}</div><div class='delta'>-{stats['chars_saved']} ({stats['pct_saved']}%)</div></div>",unsafe_allow_html=True)
        k2.markdown(f"<div class='box'><div class='label'>Tokens →</div><div class='value'>{stats['tokens_before']} → {stats['tokens_after']}</div><div class='delta'>-{stats['tokens_saved']}</div></div>",unsafe_allow_html=True)
        k3.markdown(f"<div class='box'><div class='label'>Budget OK</div><div class='value'>{'✅' if stats['respected_budget'] else '❌'}</div></div>",unsafe_allow_html=True)
        k4.markdown(f"<div class='box'><div class='label'>Étapes</div><div class='value'>{len(stats['steps'])}</div></div>",unsafe_allow_html=True)

        # Résultat + diff
        st.markdown("### Prompt optimisé")
        st.text_area(" ",opt,height=140)
        st.caption("⌘/Ctrl+C pour copier après sélection.")
        st.markdown("### Diff (mots supprimés/ajoutés)")
        st.markdown(f"<div class='diff'>{ndiff_html(base,opt)}</div>",unsafe_allow_html=True)

        # coût
        tb,ta=stats["tokens_before"],stats["tokens_after"]
        pb,cb=int(tb*0.7),tb-int(tb*0.7)
        pa,ca=int(ta*0.7),ta-int(ta*0.7)
        cost_b,cost_a=estimate_cost(pb,cb,st.session_state["model"]),estimate_cost(pa,ca,st.session_state["model"])
        c1,c2,c3=st.columns(3)
        c1.markdown(f"<div class='card'><div class='small'>Coût avant</div><b>${cost_b}</b></div>",unsafe_allow_html=True)
        c2.markdown(f"<div class='card'><div class='small'>Coût après</div><b>${cost_a}</b></div>",unsafe_allow_html=True)
        c3.markdown(f"<div class='card'><div class='small'>Économie</div><b>${round(cost_b-cost_a,6)}</b></div>",unsafe_allow_html=True)

        # Historique léger
        hist=st.session_state.setdefault("_opt_history",[])
        hist.append({"tokens_before":tb,"tokens_after":ta,"cost_before":cost_b,"cost_after":cost_a})
        st.session_state["_opt_history"]=hist[-50:]
        st.download_button("⬇️ Télécharger (.txt)",data=opt.encode("utf-8"),file_name="prompt_optimise.txt",mime="text/plain")
else:
    st.info("Colle un prompt puis clique **Optimiser**.")

# ───── Mini-historique ─────
if st.session_state.get("_opt_history"):
    st.markdown("### Historique rapide (tokens)")
    df=pd.DataFrame(st.session_state["_opt_history"])
    df["run"]=range(1,len(df)+1)
    st.line_chart(df.set_index("run")[["tokens_before","tokens_after"]])