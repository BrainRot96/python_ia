# format_converter_app.py
# ------------------------------------------------------------
# 🔁 Convertisseur JSON ↔︎ YAML + 🧪 Validateur (schéma + données)
# ------------------------------------------------------------
import json
from io import BytesIO
from typing import Any, Tuple

import streamlit as st
import yaml
from jsonschema import Draft7Validator, validate as js_validate
from jsonschema.exceptions import SchemaError, ValidationError
from jsonschema.validators import Draft202012Validator

# ========== Page ==========
st.set_page_config(
    page_title="JSON ↔︎ YAML Converter",
    page_icon="🔁",
    layout="centered",
)

st.title("🔁 Convertisseur JSON ↔︎ YAML")
st.caption("Charge un fichier ou colle du texte → convertis → (option) valide avec un schéma → télécharge.")

# ========== Utils ==========
def guess_ext(filename: str) -> str:
    name = (filename or "").lower()
    if name.endswith(".json"):
        return "json"
    if name.endswith(".yaml") or name.endswith(".yml"):
        return "yaml"
    return ""

def load_content(file_bytes: bytes, ext_hint: str) -> Tuple[Any, str]:
    """Parse bytes en Python obj (dict/list) selon un hint d’extension."""
    try:
        text = file_bytes.decode("utf-8")
    except UnicodeDecodeError:
        return None, "Encodage non UTF-8. Convertis le fichier en UTF-8."
    try:
        if ext_hint == "json":
            return json.loads(text), ""
        elif ext_hint in ("yaml", "yml"):
            return yaml.safe_load(text), ""
        else:
            # Essaie JSON puis YAML
            try:
                return json.loads(text), ""
            except Exception:
                return yaml.safe_load(text), ""
    except Exception as e:
        return None, f"Erreur de parsing ({ext_hint.upper()}): {e}"

def dump_content(data: Any, target: str) -> Tuple[str, bytes]:
    """Sérialise vers JSON ou YAML (aperçu texte + bytes)."""
    if target == "json":
        text = json.dumps(data, ensure_ascii=False, indent=2)
        return text, text.encode("utf-8")
    # YAML
    text = yaml.safe_dump(data, sort_keys=False, allow_unicode=True)
    return text, text.encode("utf-8")

def format_error_path(err) -> str:
    """Chemin lisible vers l’élément en erreur (ex: root.items[3].name)"""
    parts = ["root"]
    for p in err.absolute_path:
        if isinstance(p, int):
            parts.append(f"[{p}]")
        else:
            parts.append(f".{p}")
    return "".join(parts).replace("..", ".")

# ========== Barre latérale ==========
with st.sidebar:
    st.header("Paramètres")
    st.write("Si tu colles du texte brut et qu’on ne peut pas deviner le format, on utilisera ce format cible :")
    target_format = st.radio(
        "Format cible",
        options=["JSON", "YAML"],
        horizontal=True,
        key="target_format_radio",
    )
    st.divider()

# ========== SECTION A — Conversion + (option) Validation ==========
st.header("A) Conversion & Validation")

schema_file = st.file_uploader(
    "📐 Schéma (JSON/YAML) – optionnel",
    type=["json", "yaml", "yml"],
    key="schema_uploader_A",
)
schema_text = st.text_area(
    "…ou colle le schéma ici (optionnel)",
    height=160,
    key="schema_text_A",
)

strict_on_error = st.checkbox(
    "Bloquer la conversion si les données ne valident pas le schéma",
    value=False,
    key="strict_A",
)

st.subheader("1) Source")
c1, c2 = st.columns(2)
with c1:
    uploaded = st.file_uploader(
        "📁 Fichier (.json / .yaml / .yml)",
        type=["json", "yaml", "yml"],
        key="content_uploader_A",
    )
with c2:
    pasted = st.text_area(
        "…ou colle directement ton contenu (JSON ou YAML)",
        height=180,
        key="paste_A",
    )

data = None
src_ext = ""
err = ""

if uploaded:
    src_ext = guess_ext(uploaded.name) or "json"
    data, err = load_content(uploaded.read(), src_ext)
elif pasted.strip():
    # on tente JSON puis YAML
    data, err = load_content(pasted.encode("utf-8"), "json")
    if err:
        data, err = load_content(pasted.encode("utf-8"), "yaml")
        src_ext = "yaml" if not err else ""
    else:
        src_ext = "json"

if err:
    st.error(err)

if data is not None and not err:
    st.success(f"✅ Données chargées ({src_ext.upper() or 'auto'})")
    st.code(json.dumps(data, ensure_ascii=False, indent=2), language="json")

    # 1.b) Validation optionnelle
    validation_ok = True
    schema = None
    schema_err = ""

    if schema_file is not None:
        s_ext = guess_ext(schema_file.name)
        schema, schema_err = load_content(schema_file.read(), s_ext or "json")
    elif schema_text.strip():
        schema, schema_err = load_content(schema_text.encode("utf-8"), "json")
        if schema_err:
            schema, schema_err = load_content(schema_text.encode("utf-8"), "yaml")

    if schema_err:
        st.warning(f"Schéma non chargé : {schema_err}")

    if schema:
        try:
            validator = Draft7Validator(schema)
        except Exception as e:
            st.error(f"❌ Schéma invalide : {e}")
            validation_ok = False
        else:
            errors = sorted(validator.iter_errors(data), key=lambda e: e.path)
            if errors:
                validation_ok = False
                st.error("❌ Données INVALIDES (au regard du schéma) :")
                for i, e in enumerate(errors, 1):
                    st.markdown(
                        f"- **Erreur {i}** — chemin: `{format_error_path(e)}`  \n"
                        f"  Raison: *{e.message}*"
                    )
            else:
                st.success("🟢 Données valides pour le schéma fourni.")

    if strict_on_error and not validation_ok:
        st.stop()

    # 2) Conversion
    st.subheader("2) Conversion")
    if src_ext == "json":
        convert_to = "yaml"
    elif src_ext == "yaml":
        convert_to = "json"
    else:
        convert_to = "yaml" if st.session_state["target_format_radio"].lower() == "yaml" else "json"

    preview_text, out_bytes = dump_content(data, convert_to)
    st.write(f"**Format de sortie :** `{convert_to.upper()}`")
    st.code(preview_text, language=("yaml" if convert_to == "yaml" else "json"))

    # 3) Téléchargement
    st.subheader("3) Téléchargement")
    dl_name = f"converted.{ 'yml' if convert_to=='yaml' else 'json' }"
    st.download_button(
        "⬇️ Télécharger",
        data=out_bytes,
        file_name=dl_name,
        mime=("application/x-yaml" if convert_to == "yaml" else "application/json"),
        key="download_btn_A",
    )
else:
    st.info("⤴️ Dépose un fichier ou colle du contenu pour commencer la conversion.")

st.divider()

# ========== SECTION B — Validateur rapide (schéma + données) ==========
st.header("B) 🧪 Test rapide du validateur (schéma + données)")

# --- Init (clé stables) ---
if "schema_text_B" not in st.session_state:
    st.session_state.schema_text_B = ""
if "data_text_B" not in st.session_state:
    st.session_state.data_text_B = ""

def parse_json_or_yaml(text: str):
    text = (text or "").strip()
    if not text:
        return None, "vide"
    # Essai JSON puis YAML
    try:
        return json.loads(text), "json"
    except Exception:
        pass
    try:
        return yaml.safe_load(text), "yaml"
    except Exception as e:
        return None, f"parse_error: {e}"

def example_payloads() -> Tuple[str, str]:
    schema_ex = {
        "type": "object",
        "required": ["nom", "months", "expo", "hauteur_cm"],
        "properties": {
            "nom": {"type": "string"},
            "couleur": {"type": "string"},
            "months": {
                "type": "array",
                "items": {"type": "integer", "minimum": 1, "maximum": 12},
                "minItems": 1
            },
            "expo": {
                "type": "array",
                "items": {"type": "string", "enum": ["soleil", "mi-ombre", "ombre"]},
                "minItems": 1
            },
            "hauteur_cm": {
                "type": "array",
                "items": {"type": "integer", "minimum": 1},
                "minItems": 2, "maxItems": 2
            },
            "entretien": {"type": "string", "enum": ["faible", "moyen", "élevé"]}
        },
        "additionalProperties": True
    }
    data_ex = {
        "nom": "Mahonia × media",
        "couleur": "jaune",
        "months": [11, 12, 1, 2, 3],
        "expo": ["ombre", "mi-ombre"],
        "hauteur_cm": [150, 300],
        "entretien": "faible"
    }
    return (
        json.dumps(schema_ex, ensure_ascii=False, indent=2),
        json.dumps(data_ex, ensure_ascii=False, indent=2),
    )

colS, colD = st.columns(2)
with colS:
    schema_str_B = st.text_area(
        "Colle ton schéma ici",
        key="schema_text_B",
        height=220,
        placeholder='Ex: { "type":"object", "properties": { "nom": {"type":"string"} } }',
    )
with colD:
    data_str_B = st.text_area(
        "Colle tes données ici",
        key="data_text_B",
        height=220,
        placeholder='Ex: { "nom": "Mahonia × media" }',
    )

cA, cB, _ = st.columns([1,1,4])
with cA:
    if st.button("Remplir avec un exemple", key="example_btn_B"):
        s_ex, d_ex = example_payloads()
        st.session_state.schema_text_B = s_ex
        st.session_state.data_text_B = d_ex
        st.rerun()

with cB:
    run_validation = st.button("✅ Valider maintenant", key="validate_btn_B")

if run_validation:
    schema_obj, _ = parse_json_or_yaml(st.session_state.get("schema_text_B", ""))
    data_obj, _ = parse_json_or_yaml(st.session_state.get("data_text_B", ""))

    if schema_obj is None:
        st.error("Schéma: introuvable ou invalide (JSON/YAML non parsé).")
    elif data_obj is None:
        st.error("Données: introuvables ou invalides (JSON/YAML non parsé).")
    else:
        # 1) Vérifier que le schéma lui-même est valide
        try:
            Draft202012Validator.check_schema(schema_obj)
        except SchemaError as e:
            st.error(f"❌ Schéma invalide : {e.message}")
        else:
            # 2) Valider les données contre le schéma
            try:
                js_validate(instance=data_obj, schema=schema_obj)
                st.success("✅ Données VALIDE(S) pour le schéma donné.")
            except ValidationError as e:
                st.error("❌ Données INVALIDES pour ce schéma.")
                st.write("Message :", e.message)
                if e.path:
                    st.write("Chemin :", " → ".join(map(str, e.path)))
                with st.expander("Détail complet de l’erreur"):
                    st.exception(e)

st.caption("Astuce : donne toujours des `key` uniques à tes widgets Streamlit pour éviter les DuplicateWidgetID.")
