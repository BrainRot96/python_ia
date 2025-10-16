# prompts/templates.py
from dataclasses import dataclass
from typing import Dict

@dataclass(frozen=True)
class PromptTemplate:
    name: str
    system: str
    user: str

def render_template(tpl: PromptTemplate, **kwargs) -> Dict[str, str]:
    try:
        system_txt = tpl.system.format(**kwargs)
        user_txt   = tpl.user.format(**kwargs)
    except KeyError as e:
        raise ValueError(f"Variable manquante pour le template '{tpl.name}': {e}")
    return {"system": system_txt, "user": user_txt}

# === Templates ===

SUMMARY_TEMPLATE = PromptTemplate(
    name="summary",
    system="Tu es un assistant clair et factuel. Réponds en français.",
    user=(
        "Résume le texte suivant en {n_sentences} phrase(s) max, style concis :\n"
        "----\n{context}\n----"
    ),
)

QA_TEMPLATE = PromptTemplate(
    name="qa",
    system="Tu es un expert pédagogue. Réponds en français, de façon précise et structurée.",
    user=(
        "Question : {question}\n"
        "Contexte (facultatif) : {context}\n\n"
        "Donne une réponse directe et courte (puis détaille si utile)."
    ),
)
