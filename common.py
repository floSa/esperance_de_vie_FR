"""Constantes, palette et utilitaires partagés par toutes les pages."""

from datetime import date

import streamlit as st

from data.embedded import COHORT_SURVIVAL

# Palette du projet (fixe par entité — jamais recyclée)
COLOR_FEMMES = "#ec4899"
COLOR_FEMMES_ZONE = "rgba(236, 72, 153, 0.2)"
COLOR_HOMMES = "#0284c7"
COLOR_HOMMES_ZONE = "rgba(2, 132, 199, 0.2)"
COLOR_DECEDES = "rgba(248, 113, 113, 0.35)"
COLOR_E0 = "#f97316"  # espérance de vie (tirets orange)
# Zone « encore en vie » : neutre volontairement. La teindre selon le sexe
# faisait croire à une seconde variable alors qu'il n'y en a qu'une.
COLOR_VIVANTS_ZONE = "rgba(148, 163, 184, 0.22)"

SEX_COLORS = {"femmes": COLOR_FEMMES, "hommes": COLOR_HOMMES}
SEX_ZONES = {"femmes": COLOR_FEMMES_ZONE, "hommes": COLOR_HOMMES_ZONE}
SEX_LABELS = {"femmes": "Femmes", "hommes": "Hommes"}

CURRENT_YEAR = date.today().year

SOURCE_NOTE = (
    "*Sources : INSEE (API Melodi), Eurostat (demo_mlexpec, demo_mlifetable), "
    "Our World in Data · Provenance détaillée dans `data/sources/manifest.json` · "
    "Survie par génération estimée à ±5 %*"
)


# ---------------------------------------------------------------------------
# Habillage / thème
# ---------------------------------------------------------------------------

def plotly_template() -> str:
    """Template Plotly adapté au thème Streamlit courant (clair ou sombre)."""
    base = None
    try:
        base = st.context.theme.type
    except Exception:
        try:
            base = st.get_option("theme.base")
        except Exception:
            base = None
    return "plotly_dark" if base == "dark" else "plotly_white"


def apply_layout(fig, **kwargs):
    """Applique le template + fonds transparents (compatibilité dark mode)."""
    fig.update_layout(
        template=plotly_template(),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        **kwargs,
    )
    return fig


# La valeur affichée au-dessus du curseur est le repère de lecture de la page ;
# sa taille par défaut la rend illisible à côté des métriques.
_STYLE_CURSEURS = """
<style>
  [data-testid="stSliderThumbValue"] {
      font-size: 1.35rem !important;
      font-weight: 700 !important;
      white-space: nowrap;
  }
  /* Dégage la hauteur nécessaire pour que la valeur ne chevauche pas le label. */
  [data-testid="stSlider"] { padding-top: 1.1rem; }
  [data-testid="stSliderTickBar"] { font-size: .8rem; opacity: .65; }
</style>
"""


def render_sidebar():
    # Appelé par toutes les pages : c'est le point d'injection du style commun.
    st.markdown(_STYLE_CURSEURS, unsafe_allow_html=True)
    st.sidebar.title("📊 Espérance de vie")
    st.sidebar.caption("France & Europe · INSEE / Eurostat / OWID")
    st.sidebar.markdown("---")
    st.sidebar.info(
        "**Sources** : INSEE (API Melodi), Eurostat (demo_mlexpec, "
        "demo_mlifetable), Our World in Data.\n\n"
        "Rafraîchir : `uv run python -m scripts.refresh_data`"
    )


def source_note():
    st.markdown("---")
    st.markdown(SOURCE_NOTE)


def note_lecture(lecture: str, source: str | None = None):
    """Note de lecture affichée sous un graphique.

    `lecture` explique comment déchiffrer le graphique — ce que portent les
    axes, ce que signifie une courbe qui monte, le piège éventuel. `source`
    indique d'où viennent les chiffres tracés.
    """
    st.markdown(
        f"<div style='border-left:3px solid rgba(128,128,128,.35);"
        f"padding:.1rem 0 .1rem .8rem;margin:.2rem 0 .6rem 0;'>"
        f"<strong>Comment lire ce graphique</strong><br>{lecture}</div>",
        unsafe_allow_html=True,
    )
    if source:
        st.caption(f"Source : {source}")


def download_csv(df, page_name: str):
    st.download_button(
        label="⬇ Télécharger les données (CSV)",
        data=df.to_csv(index=False).encode("utf-8"),
        file_name=f"esperance_vie_{page_name}.csv",
        mime="text/csv",
        key=f"dl_{page_name}",
    )


def persist(key: str, default):
    """Initialise une clé de session et la garde en vie entre les pages.

    Streamlit supprime l'état d'un widget quand sa page n'est plus affichée ;
    la ré-affectation permet de mémoriser les sélections inter-pages.
    """
    if key not in st.session_state:
        st.session_state[key] = default
    st.session_state[key] = st.session_state[key]
    return st.session_state[key]


def fr_num(x: float, dec: int = 1) -> str:
    """Formate un nombre à la française : 12 345,6."""
    s = f"{x:,.{dec}f}"
    return s.replace(",", " ").replace(".", ",")


# ---------------------------------------------------------------------------
# Survie par cohorte (interpolation des ancres embarquées)
# ---------------------------------------------------------------------------

def interp_survival(cohort_data: list[tuple], age: float) -> float | None:
    """Interpolation linéaire entre ancres [(age, pct), ...].

    Retourne `None` au-delà de la dernière ancre. Prolonger la pente du dernier
    segment donnait des résultats aberrants : pour les générations récentes,
    cette dernière ancre est leur âge atteint aujourd'hui, et le segment final
    ne couvre parfois qu'une seule année — une pente bien trop raide pour être
    extrapolée sur plusieurs décennies.
    """
    ages = [a for a, _ in cohort_data]
    pcts = [p for _, p in cohort_data]
    if age <= ages[0]:
        return float(pcts[0])
    if age > ages[-1]:
        return None
    for i in range(1, len(ages)):
        if age <= ages[i]:
            a0, a1 = ages[i - 1], ages[i]
            p0, p1 = pcts[i - 1], pcts[i]
            return p0 + (p1 - p0) * (age - a0) / (a1 - a0)
    return float(pcts[-1])


def get_cohort_survival(sex: str, birth_year: int, age: float) -> float | None:
    """% d'une génération encore en vie à un âge donné.

    Seules les générations de référence dont les données atteignent réellement
    cet âge sont utilisées ; interpoler avec une génération trop jeune pour
    l'avoir atteint faisait apparaître un creux de survie entre les
    générations 1960 et 1970, démographiquement impossible.

    Retourne `None` si aucune génération de référence n'a encore atteint cet âge.
    """
    data = COHORT_SURVIVAL[sex]
    couvrantes = sorted(y for y, ancres in data.items() if ancres[-1][0] >= age)
    if not couvrantes:
        return None

    def valeur(annee: int) -> float:
        return float(interp_survival(data[annee], age))

    # Aucune extrapolation entre générations : au-delà de la dernière
    # génération ayant atteint cet âge, on retient sa valeur telle quelle.
    # Prolonger la tendance amplifiait un écart de 5 ans de naissance sur
    # 10 ans de projection, au prix d'une survie qui remontait avec l'âge.
    if birth_year <= couvrantes[0]:
        return valeur(couvrantes[0])
    if birth_year >= couvrantes[-1]:
        return valeur(couvrantes[-1])

    lo = max(y for y in couvrantes if y <= birth_year)
    hi = min(y for y in couvrantes if y >= birth_year)
    if hi == lo:
        return valeur(lo)
    p_lo, p_hi = valeur(lo), valeur(hi)
    return p_lo + (p_hi - p_lo) * (birth_year - lo) / (hi - lo)
