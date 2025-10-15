# app.py — Générateur de palette mellifère 4 saisons (climat parisien)
import streamlit as st
from dataclasses import dataclass
from typing import List, Set, Tuple
import csv
from io import StringIO

# ---------- Config UI ----------
st.set_page_config(page_title="Palette mellifère 4 saisons", page_icon="🌼", layout="wide")

# --- Style global (cards + badges) ---
st.markdown("""
<style>
.card{border:1px solid #eaeaea;border-radius:14px;padding:14px;margin:8px 0;background:#fff}
.badge{display:inline-block;padding:2px 8px;border-radius:999px;font-size:12px;margin-right:6px;border:1px solid #ddd}
.badge.saison-hiver{background:#eef5ff;border-color:#cfe0ff}
.badge.saison-printemps{background:#ecfff0;border-color:#c8f2d3}
.badge.saison-ete{background:#fff6e6;border-color:#ffd49a}
.badge.saison-automne{background:#fff0ec;border-color:#ffc9b8}
.badge.tag{background:#f6f7f9}
hr.soft{border:0;border-top:1px solid #eee;margin:10px 0}
</style>
""", unsafe_allow_html=True)

st.title("🌼 Générateur de palette mellifère – 4 saisons")
st.caption("Choisis tes contraintes → obtiens une palette couvrant hiver, printemps, été, automne.")
tab_sel, tab_heat, tab_curve, tab_nectar, tab_text = st.tabs(
    ["🧺 Sélection", "🔥 Heatmap", "📈 Courbe", "🍯 Nectar", "🧠 Analyse"]
)

# ---------- Utilitaires ----------
SEASON_OF_MONTH = {
    1: "hiver", 2: "hiver", 12: "hiver",
    3: "printemps", 4: "printemps", 5: "printemps",
    6: "été", 7: "été", 8: "été",
    9: "automne", 10: "automne", 11: "automne",
}

def months_to_seasons(months: Set[int]) -> Set[str]:
    return {SEASON_OF_MONTH[m] for m in months if m in SEASON_OF_MONTH}

def calendar_line(months: Set[int]) -> str:
    # Représentation 1→12, █ = floraison, · = hors floraison
    return "".join("█" if m in months else "·" for m in range(1, 13))

# --- Analyse couleurs & saisons (utilitaires) ---
COLOR_FAMILY = {
    "jaune": "chaud", "or": "chaud", "orange": "chaud", "rouge": "chaud",
    "blanc": "neutre", "crème": "neutre", "vert": "neutre",
    "rose": "doux", "rosé": "doux",
    "mauve": "froid", "violet": "froid", "bleu": "froid"
}

def color_family(c: str) -> str:
    if not c:
        return "neutre"
    c = c.lower()
    return next((fam for k, fam in COLOR_FAMILY.items() if k in c), "neutre")

def months_from_rows(rows):
    months = set()
    for r in rows:
        line = r.get("mois_floraison_1_12", "")
        for m in range(1, 13):
            if len(line) >= m and line[m-1] == "█":
                months.add(m)
    return months

def seasons_from_months(ms: set[int]) -> set[str]:
    _MAP = {
        1:"hiver",2:"hiver",12:"hiver",
        3:"printemps",4:"printemps",5:"printemps",
        6:"été",7:"été",8:"été",
        9:"automne",10:"automne",11:"automne"
    }
    return {_MAP[m] for m in ms if m in _MAP}

# ---------- Modèle de données ----------
@dataclass
class Shrub:
    nom: str
    couleur: str
    months: Set[int]
    expo: Set[str]
    hauteur_cm: Tuple[int,int]
    racines: str
    notes: str = ""
    entretien: str = "moyen"                # "faible", "moyen", "élevé"
    sol: Set[str] = frozenset({"normal"})   # {"drainant","normal","lourd"}
    secheresse: str = "moyenne"             # "bonne","moyenne","faible"
    racinaire_type: str = "fibreux"         # "fibreux","drageonnant","traçant"
    nectar: float = 1.0  # score de nectar (par défaut = 1.0)

    @property
    def saisons(self) -> Set[str]:
        return months_to_seasons(self.months)

# ---------- Catalogue (extrait, mellifères compatibles urbain/Paris) ----------
CATA: List[Shrub] = [
    Shrub("Mahonia × media","jaune",{11,12,1,2,3},{"ombre","mi-ombre"},(150,300),
          "drageonnant/rhizomes, modéré","nectar/pollen hiver",
          entretien="faible", sol={"normal","drainant"}, secheresse="moyenne", racinaire_type="drageonnant"),

    Shrub("Viburnum tinus (laurier-tin)","blanc/rosé",{11,12,1,2,3,4},{"soleil","mi-ombre"},(150,250),
          "fibreux, non agressif","floraison longue",
          entretien="faible", sol={"normal","drainant"}, secheresse="moyenne", racinaire_type="fibreux"),

    Shrub("Choisya ternata (oranger du Mexique)","blanc",{4,5,9,10},{"soleil","mi-ombre"},(150,250),
          "fibreux superficiel","remontée d’automne",
          entretien="faible", sol={"drainant"}, secheresse="bonne", racinaire_type="fibreux"),

    Shrub("Abelia × grandiflora","blanc rosé",{6,7,8,9,10},{"soleil","mi-ombre"},(120,200),
          "fibreux","mellifère, été-automne",
          entretien="faible", sol={"normal","drainant"}, secheresse="moyenne", racinaire_type="fibreux"),
]
# ➕ Extension du catalogue : arbustes & vivaces très mellifères (Paris/urbain)
CATA.extend([
    # --- ARBUSTES ---

    Shrub("Sarcococca confusa", "blanc", {1,2,3}, {"ombre","mi-ombre"}, (60,150),
          "drageonnant lent", "parfum hivernal, très mellifère",
          entretien="faible", sol={"normal","drainant"}, secheresse="moyenne", racinaire_type="drageonnant"),

    Shrub("Lonicera fragrantissima (chèvrefeuille d'hiver)", "blanc", {1,2,3}, {"soleil","mi-ombre"}, (150,250),
          "fibreux", "floraison hivernale parfumée, nectar précoce",
          entretien="faible", sol={"normal"}, secheresse="moyenne", racinaire_type="fibreux"),

    Shrub("Ribes sanguineum (groseillier à fleurs)", "rose", {3,4,5}, {"soleil","mi-ombre"}, (150,250),
          "fibreux", "ressource nectar/pollen de début de saison",
          entretien="faible", sol={"normal"}, secheresse="moyenne", racinaire_type="fibreux"),

    Shrub("Ceanothus 'Gloire de Versailles'", "bleu", {6,7,8,9}, {"soleil"}, (150,200),
          "fibreux", "très mellifère, refloraison possible",
          entretien="faible", sol={"drainant"}, secheresse="bonne", racinaire_type="fibreux"),

    Shrub("Caryopteris × clandonensis", "bleu", {8,9,10}, {"soleil"}, (80,120),
          "fibreux", "gros apport nectar fin d’été-automne",
          entretien="faible", sol={"drainant"}, secheresse="bonne", racinaire_type="fibreux"),

    Shrub("Lavandula angustifolia (lavande vraie)", "violet", {6,7,8}, {"soleil"}, (40,70),
          "fibreux", "emblématique pour abeilles",
          entretien="faible", sol={"drainant"}, secheresse="bonne", racinaire_type="fibreux"),

    Shrub("Salvia rosmarinus (romarin)", "bleu", {3,4,5}, {"soleil"}, (80,150),
          "fibreux", "mellifère + aromatique",
          entretien="faible", sol={"drainant"}, secheresse="bonne", racinaire_type="fibreux"),

    Shrub("Hypericum ‘Hidcote’ (millepertuis)", "jaune", {6,7,8,9}, {"soleil","mi-ombre"}, (80,120),
          "fibreux", "floraison longue, robuste",
          entretien="faible", sol={"normal"}, secheresse="moyenne", racinaire_type="fibreux"),

    Shrub("Escallonia rubra", "rose", {6,7,8,9}, {"soleil"}, (150,250),
          "fibreux", "mellifère, supporte bien les conditions urbaines",
          entretien="faible", sol={"drainant"}, secheresse="moyenne", racinaire_type="fibreux"),

    Shrub("Heptacodium miconioides", "blanc", {8,9,10}, {"soleil"}, (300,500),
          "fibreux", "ressource tardive très appréciée",
          entretien="moyen", sol={"normal","drainant"}, secheresse="moyenne", racinaire_type="fibreux"),

    # --- VIVACES (ajoutées ici comme “petits arbustes” pour rester compatibles avec la classe) ---

    Shrub("Echinacea purpurea", "rose", {7,8,9}, {"soleil"}, (60,100),
          "fibreux", "disques très nectarifères, attirent pollinisateurs",
          entretien="faible", sol={"normal","drainant"}, secheresse="moyenne", racinaire_type="fibreux"),

    Shrub("Achillea millefolium (achillée)", "jaune", {6,7,8,9}, {"soleil"}, (40,80),
          "fibreux", "mellifère, résistante à la sécheresse",
          entretien="faible", sol={"drainant","normal"}, secheresse="bonne", racinaire_type="fibreux"),

    Shrub("Nepeta × faassenii (herbe-aux-chats)", "mauve", {5,6,7,8,9}, {"soleil"}, (30,50),
          "fibreux", "floraison étalée, très visitée",
          entretien="faible", sol={"drainant"}, secheresse="bonne", racinaire_type="fibreux"),

    Shrub("Salvia nemorosa", "violet", {6,7,8,9}, {"soleil"}, (40,70),
          "fibreux", "épis très nectarifères, remontées si rabattue",
          entretien="faible", sol={"drainant"}, secheresse="bonne", racinaire_type="fibreux"),

    Shrub("Gaura lindheimeri", "blanc/rosé", {6,7,8,9,10}, {"soleil"}, (60,100),
          "fibreux", "nuages légers, longue floraison",
          entretien="faible", sol={"drainant"}, secheresse="bonne", racinaire_type="fibreux"),

    Shrub("Agastache foeniculum", "mauve", {7,8,9,10}, {"soleil"}, (60,120),
          "fibreux", "très mellifère et aromatique",
          entretien="faible", sol={"drainant"}, secheresse="bonne", racinaire_type="fibreux"),
])

# --- Ajouts au catalogue : arbustes & vivaces mellifères (Paris-friendly) ---
# ⚠️ Version sans doublons (uniquement des espèces non ajoutées plus haut)
CATA += [
    # --------- ARBUSTES (nouveaux uniquement) ---------
    Shrub("Ceanothus 'Concha'", "bleu", {5,6}, {"soleil"}, (150,250),
          "fibreux", "spectaculaire au printemps (variété différente)",
          entretien="faible", sol={"drainant"}, secheresse="bonne", racinaire_type="fibreux"),

    Shrub("Elaeagnus × ebbingei", "blanc", {10,11,12}, {"soleil","mi-ombre"}, (200,300),
          "fibreux", "très parfumé en automne, robuste urbain",
          entretien="faible", sol={"normal","drainant"}, secheresse="bonne", racinaire_type="fibreux"),

    Shrub("Arbutus unedo (arbousier)", "blanc", {10,11,12}, {"soleil"}, (250,400),
          "fibreux", "floraison automnale + fruits",
          entretien="faible", sol={"drainant","normal"}, secheresse="bonne", racinaire_type="fibreux"),

    # (facultatif, filtré si 'Éviter invasives' activé)
    Shrub("Buddleja davidii (arbre aux papillons)", "violet/rose/blanc", {7,8,9}, {"soleil"}, (200,300),
          "fibreux", "très mellifère mais potentiellement invasif",
          entretien="faible", sol={"drainant","normal"}, secheresse="bonne", racinaire_type="fibreux"),

    # --------- VIVACES (nouvelles uniquement) ---------
    Shrub("Hylotelephium spectabile (sedum d’automne)", "rose", {8,9,10}, {"soleil"}, (40,60),
          "fibreux", "capte l’automne, très visité",
          entretien="faible", sol={"drainant"}, secheresse="bonne", racinaire_type="fibreux"),

    Shrub("Helleborus orientalis (hellébore)", "blanc/rose/vert", {1,2,3}, {"mi-ombre","ombre"}, (30,50),
          "fibreux", "très précoce, utile en hiver",
          entretien="faible", sol={"normal","lourd"}, secheresse="moyenne", racinaire_type="fibreux"),

    Shrub("Geranium 'Rozanne'", "bleu/violet", {6,7,8,9,10}, {"soleil","mi-ombre"}, (30,40),
          "fibreux", "floraison marathon",
          entretien="faible", sol={"normal"}, secheresse="moyenne", racinaire_type="fibreux"),

    Shrub("Verbena bonariensis", "mauve", {7,8,9,10}, {"soleil"}, (100,180),
          "fibreux", "aérienne, attire papillons/abeilles",
          entretien="faible", sol={"drainant","normal"}, secheresse="moyenne", racinaire_type="fibreux"),

    Shrub("Aster (Symphyotrichum) novi-belgii", "violet/rose/blanc", {9,10}, {"soleil","mi-ombre"}, (60,120),
          "fibreux", "fin de saison, essentiel pour butineurs",
          entretien="moyen", sol={"normal"}, secheresse="moyenne", racinaire_type="fibreux"),
]
# --- Typage simple : quelles entrées du catalogue sont des vivaces ? ---
VIVACE_SET = {
    "Echinacea purpurea",
    "Achillea millefolium (achillée)",
    "Nepeta × faassenii (herbe-aux-chats)",
    "Salvia nemorosa",
    "Gaura lindheimeri",
    "Agastache foeniculum",
    "Hylotelephium spectabile (sedum d’automne)",
    "Helleborus orientalis (hellébore)",
    "Geranium 'Rozanne'",
    "Verbena bonariensis",
    "Aster (Symphyotrichum) novi-belgii",
}

def plant_type(s: Shrub) -> str:
    """Retourne 'vivace' si le nom est listé comme vivace, sinon 'arbuste'."""
    return "vivace" if s.nom in VIVACE_SET else "arbuste"


def nectar_scores(plants: List[Shrub], mode: str = "égal") -> list[float]:
    """
    Calcule un score nectar par mois (1..12) en sommant les contributions
    des plantes sélectionnées.

    mode:
      - "égal"      : chaque plante pèse 1
      - "par taille": poids = hauteur moyenne (cm) / 100
      - "par type"  : arbuste = 1.0 ; vivace = 0.7
    """
    scores = [0.0] * 12
    for s in plants:
        if mode == "par taille":
            w = (s.hauteur_cm[0] + s.hauteur_cm[1]) / 2 / 100.0
        elif mode == "par type":
            w = 1.0 if plant_type(s) == "arbuste" else 0.7
        else:
            w = 1.0

        for m in s.months:
            if 1 <= m <= 12:
                scores[m - 1] += w
    return scores

# ---------- Sidebar / paramètres ----------
with st.sidebar:
    st.header("Paramètres")
    target_seasons = set(st.multiselect(
        "Saisons à couvrir",
        ["hiver","printemps","été","automne"],
        default=["hiver","printemps","été","automne"]
    ))
    exposures = set(st.multiselect(
        "Exposition acceptée",
        ["soleil","mi-ombre","ombre"],
        default=["soleil","mi-ombre"]
    ))
    hmin, hmax = st.slider("Hauteur (cm)", 20, 320, (60, 220), step=10)
    max_plants = st.slider("Nombre max de plantes", 3, 8, 6)

    st.divider()
    st.subheader("Contraintes avancées")
    want_low_maintenance = st.checkbox("Faible entretien", value=False)
    need_draining_soil   = st.checkbox("Sol drainant", value=False)
    drought_tolerant     = st.checkbox("Tolérance à la sécheresse", value=False)
    avoid_drageonnant    = st.checkbox("Éviter systèmes drageonnants/traçants", value=False)
    avoid_invasive       = st.checkbox("Éviter espèces potentiellement invasives", value=True)

    st.divider()
    st.subheader("Strates")
    allowed_strata = set(st.multiselect(
        "Strates autorisées",
        ["basse","moyenne","haute"],
        default=["basse","moyenne","haute"]
    ))
    balance_strata = st.checkbox("Équilibrer par strates (≈ 1/3 chacune)", value=False)

    st.divider()
    st.subheader("Type de plante")
    type_choice = st.selectbox(
        "Filtrer par type",
        ["mixte", "arbuste uniquement", "vivace uniquement"],
        index=0,
    )

    st.divider()
    st.subheader("Analyse IA (texte)")
    enable_text_ai = st.checkbox("Activer l’analyse textuelle", value=True)
    tone = st.selectbox("Ton", ["neutre", "enthousiaste", "pédago court"])
    detail = st.slider("Niveau de détail", 1, 5, 3)

    st.divider()
    run = st.button("Générer")

# ---------- Filtres ----------
def pass_filters(s: Shrub) -> bool:
    # Type (arbuste / vivace / mixte)
    if type_choice == "arbuste uniquement" and plant_type(s) != "arbuste":
        return False
    if type_choice == "vivace uniquement" and plant_type(s) != "vivace":
        return False

    # Expo
    if not (s.expo & exposures):
        return False

    # Hauteur
    smin, smax = s.hauteur_cm
    if smax < hmin or smin > hmax:
        return False

    # Avancés
    if want_low_maintenance and s.entretien != "faible":
        return False
    if need_draining_soil and "drainant" not in s.sol:
        return False
    if drought_tolerant and s.secheresse not in {"bonne"}:
        return False
    if avoid_drageonnant and s.racinaire_type in {"drageonnant", "traçant"}:
        return False
    if avoid_invasive and "Buddleja" in s.nom:
        return False

    return True


def stratum(s: Shrub) -> str:
    """Estime la strate via la hauteur moyenne."""
    mid = (s.hauteur_cm[0] + s.hauteur_cm[1]) / 2
    if mid < 60:
        return "basse"
    if mid <= 120:
        return "moyenne"
    return "haute"


def balanced_cover(cands: List[Shrub], target: Set[str], max_plants: int, quotas: dict) -> List[Shrub]:
    """
    Sélectionne en respectant des quotas par strates tout en couvrant d'abord
    les saisons manquantes.
    """
    remaining = set(target)
    chosen: List[Shrub] = []

    # Regrouper les candidats par strate
    pools = {"basse": [], "moyenne": [], "haute": []}
    for s in cands:
        pools[stratum(s)].append(s)

    # Trier chaque pool par contribution (nb de saisons utiles)
    for p in pools.values():
        p.sort(key=lambda x: len(x.saisons & remaining), reverse=True)

    # Remplir selon les quotas, en priorisant moyenne -> haute -> basse
    while len(chosen) < max_plants:
        missing = [k for k, q in quotas.items() if q > 0]
        if not missing:
            break

        picked = False
        for strata in ["moyenne", "haute", "basse"]:
            if strata in missing and pools[strata]:
                pools[strata].sort(key=lambda x: len(x.saisons & remaining), reverse=True)
                cand = None
                for x in pools[strata]:
                    if x not in chosen:
                        cand = x
                        break
                if cand is None:
                    continue

                chosen.append(cand)
                quotas[strata] -= 1
                remaining -= cand.saisons
                pools[strata].remove(cand)
                picked = True
                break

        if not picked:
            break

    # Compléter si places restantes
    if len(chosen) < max_plants:
        rest = [s for s in cands if s not in chosen]
        rest.sort(key=lambda x: len(x.saisons), reverse=True)
        for s in rest:
            if len(chosen) >= max_plants:
                break
            chosen.append(s)

    return chosen
def greedy_cover(cands: List[Shrub], target: Set[str], max_plants: int) -> List[Shrub]:
    """
    Sélection gloutonne simple :
    - Priorise à chaque étape la plante qui couvre le plus de saisons manquantes.
    - Si des places restent, complète avec celles qui couvrent le plus de saisons au total.
    """
    remaining = set(target)
    chosen: List[Shrub] = []
    pool = cands[:]

    while remaining and pool and len(chosen) < max_plants:
        # Trier par contribution aux saisons restantes
        pool.sort(key=lambda s: len(s.saisons & remaining), reverse=True)
        best = pool.pop(0)
        if not (best.saisons & remaining):
            # si elle n'apporte rien de nouveau, on passe
            continue
        chosen.append(best)
        remaining -= best.saisons

    # Compléter si des places restent
    if len(chosen) < max_plants and pool:
        pool.sort(key=lambda s: len(s.saisons), reverse=True)
        for s in pool:
            if len(chosen) >= max_plants:
                break
            if s not in chosen:
                chosen.append(s)

    return chosen[:max_plants]

# ---------- Corps (à mettre AVANT les onglets) ----------
rows: list[dict] = []      # existe toujours
palette: list[Shrub] = []  # existe toujours

if not run:
    pass  # on attend que l'utilisateur clique
else:
    # Candidats filtrés
    cands = [s for s in CATA if pass_filters(s)]
    if cands:
        # Sélection (avec ou sans équilibre de strates)
        if balance_strata:
            base = max_plants // max(1, len(allowed_strata))
            quotas = {s: (base if s in allowed_strata else 0) for s in ["basse","moyenne","haute"]}
            leftover = max_plants - sum(quotas.values())
            for s_name in ["moyenne","haute","basse"]:
                if s_name in allowed_strata and leftover > 0:
                    quotas[s_name] += 1
                    leftover -= 1
            palette = balanced_cover(cands, target_seasons, max_plants, quotas)
        else:
            palette = greedy_cover(cands, target_seasons, max_plants)
    else:
        palette = []

# ---------- Onglet Sélection ----------
with tab_sel:
    st.subheader("Sélection proposée")

    if not run:
        st.info("👉 Aucune sélection pour l’instant. Clique **Générer**.")
    elif not palette:
        st.warning("Aucun candidat valide avec ces filtres.")
    else:
        # Résumé couverture
        covered = set().union(*[s.saisons for s in palette])
        manque = target_seasons - covered
        if manque:
            st.info("Saisons encore peu couvertes : " + ", ".join(sorted(manque)))
        else:
            st.success("Couverture des saisons demandées : OK ✅")

        # Liste + remplissage de rows
        for i, s in enumerate(palette, start=1):
            st.markdown(f"**{i}. {s.nom}**")

            # --- Badge type (arbuste / vivace)
            t = plant_type(s)
            badge_color = "#f3f8ff" if t == "arbuste" else "#fffaf3"
            badge_border = "#a3c2ff" if t == "arbuste" else "#ffcda3"
            st.markdown(
                f"""
                <div class='card'>
                    <span class='badge tag' style='background:{badge_color};border-color:{badge_border};'>
                        🌱 {t.capitalize()}
                    </span>
                </div>
                """,
                unsafe_allow_html=True
            )

            # --- Détails plante
            st.write(
                f"- Couleur : **{s.couleur}**  \n"
                f"- Floraison (mois 1→12) : `{calendar_line(s.months)}`  \n"
                f"- Saisons : {', '.join(sorted(s.saisons))}  \n"
                f"- Expo : {', '.join(sorted(s.expo))}  \n"
                f"- Hauteur : {s.hauteur_cm[0]}–{s.hauteur_cm[1]} cm  \n"
                f"- Racines : {s.racines}  \n"
                f"- Notes : {s.notes or '—'}  \n"
                f"- Entretien : {s.entretien}  \n"
                f"- Sol : {', '.join(sorted(s.sol))}  \n"
                f"- Tolérance sécheresse : {s.secheresse}  \n"
                f"- Type racinaire : {s.racinaire_type}"
            )

            rows.append({
                "rang": i,
                "nom": s.nom,
                "couleur": s.couleur,
                "mois_floraison_1_12": calendar_line(s.months),
                "saisons": ", ".join(sorted(s.saisons)),
                "exposition": ", ".join(sorted(s.expo)),
                "hauteur_cm": f"{s.hauteur_cm[0]}–{s.hauteur_cm[1]}",
                "racines": s.racines,
                "notes": s.notes,
                "entretien": s.entretien,
                "sol": ", ".join(sorted(s.sol)),
                "secheresse": s.secheresse,
                "racinaire_type": s.racinaire_type,
                # "strate": stratum(s),
            })

        # Export CSV
        if rows:
            buf = StringIO()
            writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
            st.download_button("⬇️ Télécharger la sélection (CSV)",
                               data=buf.getvalue().encode("utf-8"),
                               file_name="palette_mellifere.csv",
                               mime="text/csv")
            
# ---------- Contrôle d'affichage (commun aux graphes) ----------
with st.expander("Affichage", expanded=False):
    m1, m2 = st.slider("Plage de mois à afficher", 1, 12, (1, 12), step=1)
# ---------- Onglet Heatmap ----------
with tab_heat:
    if rows:
        import pandas as pd
        import plotly.graph_objects as go

        cells = []
        for r in rows:
            name = r["nom"]
            line = r["mois_floraison_1_12"]
            for m in range(1, 13):
                cells.append({
                    "plante": name,
                    "mois": m,
                    "en_fleur": 1 if line[m-1] == "█" else 0
                })
        df_cells = pd.DataFrame(cells)
        df_heat = df_cells.pivot_table(index="plante", columns="mois",
                                       values="en_fleur", fill_value=0, aggfunc="max")

        # Trier par premier mois de floraison
        def first_bloom(row) -> int:
            for i, v in enumerate(row, start=1):
                if v == 1:
                    return i
            return 99
        order = sorted(df_heat.index, key=lambda p: first_bloom(df_heat.loc[p].values))
        df_heat = df_heat.loc[order]

        # Filtre de mois
        df_heat = df_heat.loc[:, list(range(m1, m2 + 1))]

        fig = go.Figure(data=go.Heatmap(
            z=df_heat.values,
            x=[f"{m:02d}" for m in df_heat.columns],
            y=df_heat.index,
            colorscale=[[0.0, "#EEEEEE"], [1.0, "#2EBB57"]],
            zmin=0, zmax=1, showscale=False,
            hovertemplate="Plante: %{y}<br>Mois: %{x}<br>Floraison: %{z}<extra></extra>",
        ))
        fig.update_layout(
            title="🌸 Calendrier visuel des floraisons",
            xaxis_title="Mois", yaxis_title="Plante",
            yaxis_autorange="reversed",
            margin=dict(l=150, r=20, t=50, b=40),
        )
        st.plotly_chart(fig, use_container_width=True)
        st.markdown("**Légende :** 🟩 = en floraison, ⬜️ = hors floraison")

    else:
        st.info("Génère une sélection pour afficher la heatmap.")

# ---------- Onglet Courbe ----------
with tab_curve:
    if rows:
        import pandas as pd
        import plotly.express as px

        lines = []
        for r in rows:
            name = r["nom"]
            line = r["mois_floraison_1_12"]
            for m in range(1, 13):
                lines.append({
                    "plante": name,
                    "mois": m,
                    "en_fleur": 1 if line[m-1] == "█" else 0
                })
        df_lines = pd.DataFrame(lines)
        df_lines = df_lines[(df_lines["mois"] >= m1) & (df_lines["mois"] <= m2)]

        fig2 = px.line(
            df_lines, x="mois", y="en_fleur", color="plante",
            markers=True,
            title="📈 Courbe de floraison par plante (0 = hors floraison, 1 = en floraison)",
            labels={"mois": "Mois (1–12)", "en_fleur": "Floraison"}
        )
        fig2.update_yaxes(tickvals=[0,1], range=[-0.05, 1.05])
        fig2.update_layout(margin=dict(l=20, r=20, t=60, b=40))
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("Génère une sélection pour afficher les courbes.")

        # ---------- Onglet Nectar ----------
with tab_nectar:
    if palette:
        import pandas as pd
        import plotly.express as px

        mode = st.selectbox(
            "Mode de pondération",
            ["égal", "type", "strates", "custom"],
            help=(
                "• égal: chaque plante = 1\n"
                "• type: arbuste 1.2 / vivace 1.0\n"
                "• strates: basse 1.0 / moyenne 1.2 / haute 1.4\n"
                "• custom: utilise l’attribut s.nectar"
            ),
        )

        scores = nectar_scores(palette, mode)
        df = pd.DataFrame({"mois": list(range(1, 13)), "score": scores})

        normalize = st.checkbox("Normaliser (0–100%)", value=False)
        if normalize and df["score"].max() > 0:
            df["score"] = (df["score"] / df["score"].max()) * 100

        fig = px.bar(
            df,
            x="mois",
            y="score",
            title="🍯 Score nectar par mois",
            labels={"mois": "Mois", "score": "Score" if not normalize else "Score (%)"},
        )
        st.plotly_chart(fig, use_container_width=True)

        st.download_button(
            "⬇️ Exporter les scores (CSV)",
            data=df.to_csv(index=False).encode("utf-8"),
            file_name="scores_nectar.csv",
            mime="text/csv",
        )
    else:
        st.info("Génère une sélection pour calculer le score nectar.")

# ---------- Onglet Analyse (IA locale) ----------
with tab_text:
    if rows and enable_text_ai:
        # Couverture
        covered_months = sorted(months_from_rows(rows))
        covered_seasons = sorted(seasons_from_months(set(covered_months)))
        # Couleurs dominantes
        fams = [color_family(r["couleur"]) for r in rows]
        dominant = (max(set(fams), key=fams.count) if fams else "neutre")

        # Strates (approx si absentes)
        strat_counts = {"basse":0,"moyenne":0,"haute":0}
        for r in rows:
            try:
                if "strate" in r:
                    strat = r["strate"]
                else:
                    hmin_s, hmax_s = r["hauteur_cm"].split("–")
                    hmid = (int(hmin_s) + int("".join(ch for ch in hmax_s if ch.isdigit()))) // 2
                    strat = "basse" if hmid < 60 else ("moyenne" if hmid <= 120 else "haute")
            except Exception:
                strat = "moyenne"
            if strat in strat_counts:
                strat_counts[strat] += 1

        low_maint = sum(1 for r in rows if r.get("entretien","moyen") == "faible")
        soils = {}
        for r in rows:
            for s in (r.get("sol","") or "").split(","):
                s = s.strip()
                if s:
                    soils[s] = soils.get(s, 0) + 1

        strengths = []
        if "hiver" in covered_seasons: strengths.append("floraison en hiver")
        if "été" in covered_seasons: strengths.append("présence estivale")
        if low_maint == len(rows): strengths.append("entretien globalement faible")
        if soils.get("drainant",0) >= max(1, len(rows)//2): strengths.append("adapté aux sols drainants")
        if dominant != "neutre": strengths.append(f"harmonie colorée {dominant}")

        manque = set(target_seasons) - set(covered_seasons)

        intro = {
            "neutre": "Synthèse de la palette générée :",
            "enthousiaste": "Belle palette ! Voici la synthèse :",
            "pédago court": "Résumé rapide :"
        }[tone]

        bullets = []
        bullets.append(f"• Couverture saisons : {', '.join(covered_seasons) or '—'} (cible : {', '.join(sorted(target_seasons))})")
        if manque:
            bullets.append(f"• Saisons à renforcer : {', '.join(sorted(manque))}")
        bullets.append(f"• Mois couverts : {', '.join(map(lambda x: f'{x:02d}', covered_months)) or '—'}")
        bullets.append(f"• Strates — basse: {strat_counts['basse']}, moyenne: {strat_counts['moyenne']}, haute: {strat_counts['haute']}")
        bullets.append(f"• Entretien faible : {low_maint}/{len(rows)} plantes")
        if soils:
            top_soils = ", ".join([f"{k} ({v})" for k,v in sorted(soils.items(), key=lambda kv: kv[1], reverse=True)[:3]])
            bullets.append(f"• Sols dominants : {top_soils}")
        bullets.append(f"• Ambiance couleur : {dominant}")

        explain = []
        if detail >= 3: explain.append("Composition pensée pour étaler les floraisons et diversifier les hauteurs. ")
        if detail >= 4: explain.append("Les teintes dominantes guident l’harmonie et la lisibilité du massif. ")
        if detail >= 5: explain.append("Ajuster l’ombre/soleil et le sol (drainant/normal) selon le site pour optimiser la vigueur. ")

        text_block = f"**{intro}**\n\n" + "\n".join(bullets) + ("\n\n" + "".join(explain) if explain else "")

        st.subheader("🧠 Analyse auto (locale)")
        st.markdown(text_block)
        st.download_button("⬇️ Télécharger l’analyse (TXT)",
                           data=text_block.encode("utf-8"),
                           file_name="analyse_palette.txt",
                           mime="text/plain")
    else:
        st.info("Active l’analyse textuelle dans la barre latérale et génère une sélection.")