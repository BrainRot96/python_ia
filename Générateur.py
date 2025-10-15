# -*- coding: utf-8 -*-
# Générateur de palettes mellifères "4 saisons" (climat parisien)
# ---------------------------------------------------------------
# Mode d'emploi :
# 1) Ajuste les PARAMÈTRES UTILISATEUR ci-dessous
# 2) Exécute :  python3 generateur_palettes_4saisons.py
# 3) Lis la sélection proposée (explication et calendrier inclus)

from dataclasses import dataclass, field
from typing import List, Set, Tuple

# ---------- PARAMÈTRES UTILISATEUR (à modifier selon besoin) ----------
TARGET_SEASONS = {"hiver", "printemps", "été", "automne"}  # quelles saisons couvrir
ALLOWED_EXPOSURES = {"soleil", "mi-ombre"}                  # expositions acceptées
HEIGHT_CM_RANGE = (40, 300)                                 # plage de hauteur souhaitée
MAX_PLANTS = 6                                              # combien d’arbustes max dans la palette
# ---------------------------------------------------------------------


# Utilitaires
SEASON_OF_MONTH = {
    1: "hiver", 2: "hiver", 12: "hiver",
    3: "printemps", 4: "printemps", 5: "printemps",
    6: "été", 7: "été", 8: "été",
    9: "automne", 10: "automne", 11: "automne",
}

def months_to_seasons(months: Set[int]) -> Set[str]:
    return {SEASON_OF_MONTH[m] for m in months if m in SEASON_OF_MONTH}

@dataclass
class Shrub:
    nom: str
    couleur: str
    months: Set[int]                 # mois de floraison (1..12)
    expo: Set[str]                   # {"soleil","mi-ombre","ombre"}
    hauteur_cm: Tuple[int, int]      # (min, max)
    racines: str                     # caractère racinaire
    notes: str = ""                  # infos utiles

    @property
    def saisons(self) -> Set[str]:
        return months_to_seasons(self.months)


# ---------- Petit catalogue (mellifères, urbain/Paris) ----------
CATA: List[Shrub] = [
    Shrub(
        nom="Mahonia × media",
        couleur="jaune",
        months={11,12,1,2,3},
        expo={"ombre","mi-ombre"},
        hauteur_cm=(150, 300),
        racines="drageonnant/rhizomes, croissance modérée",
        notes="ressource nectar/pollen en hiver"
    ),
    Shrub(
        nom="Viburnum tinus (laurier-tin)",
        couleur="blanc/rosé",
        months={11,12,1,2,3,4},
        expo={"soleil","mi-ombre"},
        hauteur_cm=(150, 250),
        racines="fibreux, non agressif",
        notes="floraison très longue hiver-printemps"
    ),
    Shrub(
        nom="Sarcococca confusa",
        couleur="blanc (très parfumé)",
        months={1,2,3},
        expo={"ombre","mi-ombre"},
        hauteur_cm=(80, 150),
        racines="fibreux, compact",
        notes="hiver; parfum; très intéressant pour butineurs tôt"
    ),
    Shrub(
        nom="Choisya ternata (oranger du Mexique)",
        couleur="blanc parfumé",
        months={4,5,9,10},  # remontée possible
        expo={"soleil","mi-ombre"},
        hauteur_cm=(150, 250),
        racines="fibreux superficiel; drainage nécessaire",
        notes="floraison printanière + remontée"
    ),
    Shrub(
        nom="Abelia × grandiflora",
        couleur="blanc rosé",
        months={6,7,8,9,10},
        expo={"soleil","mi-ombre"},
        hauteur_cm=(120, 200),
        racines="fibreux; aime les sols drainés",
        notes="très mellifère, floraison longue été-automne"
    ),
    Shrub(
        nom="Caryopteris × clandonensis (spirée bleue)",
        couleur="bleu",
        months={8,9,10},
        expo={"soleil"},
        hauteur_cm=(60, 120),
        racines="fibreux, non traçant",
        notes="fin d’été-automne, période de disette"
    ),
    Shrub(
        nom="Buddleja davidii (arbre aux papillons)",
        couleur="mauve/rose/blanc",
        months={7,8,9},
        expo={"soleil"},
        hauteur_cm=(200, 300),
        racines="fibreux, superficiel, vigoureux",
        notes="attire papillons/abeilles; choisir cultivars maîtrisés"
    ),
    Shrub(
        nom="Escallonia (groupe)",
        couleur="rose/rouge/blanc",
        months={6,7,8,9},
        expo={"soleil"},
        hauteur_cm=(100, 200),
        racines="fibreux",
        notes="bord de mer/urbain, mellifère en été"
    ),
    Shrub(
        nom="Skimmia japonica",
        couleur="blanc",
        months={4,5},
        expo={"ombre","mi-ombre"},
        hauteur_cm=(60, 120),
        racines="fibreux",
        notes="intéressant mi-ombre; baies décoratives (plants mâle/femelle)"
    ),
    Shrub(
        nom="Hebe x (variétés rustiques)",
        couleur="mauve/blanc",
        months={6,7,8,9},
        expo={"soleil","mi-ombre"},
        hauteur_cm=(60, 120),
        racines="fibreux",
        notes="selon rusticité variétale; mellifère"
    ),
]

# ---------- Filtres de base ----------
def pass_filters(s: Shrub) -> bool:
    # exposition
    if not (s.expo & ALLOWED_EXPOSURES):
        return False
    # hauteur
    hmin, hmax = s.hauteur_cm
    rmin, rmax = HEIGHT_CM_RANGE
    if hmax < rmin or hmin > rmax:
        return False
    return True

CANDIDATES: List[Shrub] = [s for s in CATA if pass_filters(s)]

# ---------- Sélection "intelligente" : couvrir les saisons visées ----------
def coverage_score(selection: List[Shrub]) -> int:
    covered = set().union(*[s.saisons for s in selection]) if selection else set()
    return len(covered & TARGET_SEASONS)

def greedy_cover(cands: List[Shrub], max_plants: int) -> List[Shrub]:
    remaining = set(TARGET_SEASONS)
    chosen: List[Shrub] = []
    pool = cands[:]

    # prioriser ceux qui apportent le plus de saisons manquantes
    while remaining and pool and len(chosen) < max_plants:
        pool.sort(key=lambda s: len(s.saisons & remaining), reverse=True)
        best = pool.pop(0)
        if not (best.saisons & remaining):
            continue
        chosen.append(best)
        remaining -= best.saisons

    # si pas couvert à 100% (rare), compléter avec les meilleurs mellifères restants
    if remaining and pool:
        # tri par nb de saisons couvertes globalement (stabilité)
        pool.sort(key=lambda s: len(s.saisons), reverse=True)
        for s in pool:
            if len(chosen) >= max_plants:
                break
            chosen.append(s)

    return chosen[:max_plants]

palette = greedy_cover(CANDIDATES, MAX_PLANTS)

# ---------- Affichage ----------
def calendar_line(months: Set[int]) -> str:
    # ex: █ sur les mois de floraison
    return "".join("█" if m in months else "·" for m in range(1,13))

print("\n🌼 Palette mellifère 4 saisons (paramètres actifs)")
print(f"  Saisons visées : {sorted(TARGET_SEASONS)}")
print(f"  Exposition     : {sorted(ALLOWED_EXPOSURES)}")
print(f"  Hauteur cm     : {HEIGHT_CM_RANGE[0]}–{HEIGHT_CM_RANGE[1]}")
print(f"  Nombre max     : {MAX_PLANTS}")

if not palette:
    print("\n⚠️ Aucune combinaison ne passe les filtres. Élargir les paramètres.")
else:
    print("\nSélection proposée :\n")
    for i, s in enumerate(palette, start=1):
        print(f"{i}. {s.nom}")
        print(f"   - Couleur   : {s.couleur}")
        print(f"   - Floraison : {', '.join(sorted(s.saisons))} | {calendar_line(s.months)}")
        print(f"                 (mois 1→12)")
        print(f"   - Expo      : {', '.join(sorted(s.expo))}")
        print(f"   - Hauteur   : {s.hauteur_cm[0]}–{s.hauteur_cm[1]} cm")
        print(f"   - Racines   : {s.racines}")
        if s.notes:
            print(f"   - Notes     : {s.notes}")
        print()

    # Bilan de couverture
    covered = set().union(*[s.saisons for s in palette])
    manquantes = sorted(TARGET_SEASONS - covered)
    if manquantes:
        print(f"⚠️ Saisons encore peu couvertes : {manquantes}")
    else:
        print("✅ Couverture des saisons demandées : OK")