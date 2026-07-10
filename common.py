"""Constantes, palette et utilitaires partagés par toutes les pages."""

import streamlit as st

from data.embedded import COHORT_SURVIVAL

# Palette du projet (fixe par entité — jamais recyclée)
COLOR_FEMMES = "#ec4899"
COLOR_FEMMES_ZONE = "rgba(236, 72, 153, 0.2)"
COLOR_HOMMES = "#0284c7"
COLOR_HOMMES_ZONE = "rgba(2, 132, 199, 0.2)"
COLOR_DECEDES = "rgba(248, 113, 113, 0.35)"
COLOR_E0 = "#f97316"  # espérance de vie (tirets orange)

SEX_COLORS = {"femmes": COLOR_FEMMES, "hommes": COLOR_HOMMES}
SEX_ZONES = {"femmes": COLOR_FEMMES_ZONE, "hommes": COLOR_HOMMES_ZONE}
SEX_LABELS = {"femmes": "Femmes", "hommes": "Hommes"}

CURRENT_YEAR = 2026

SOURCE_NOTE = (
    "*Estimations approx. · Sources : HMD (mortality.org), INSEE tables de "
    "mortalité (Vallin & Meslé), Eurostat demo_mlexpec, DREES 2024 · "
    "Survie cohorte estimée à ±5 %*"
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


def render_sidebar():
    st.sidebar.title("📊 Espérance de vie")
    st.sidebar.caption("France & Europe · HMD / INSEE / Eurostat")
    st.sidebar.markdown("---")
    st.sidebar.info(
        "**Sources** : HMD (mortality.org), INSEE tables de mortalité "
        "(Vallin & Meslé), Eurostat demo_mlexpec · "
        "Données approximées sauf import HMD direct."
    )


def source_note():
    st.markdown("---")
    st.markdown(SOURCE_NOTE)


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

def interp_survival(cohort_data: list[tuple], age: float) -> float:
    """Interpolation linéaire entre ancres [(age, pct), ...].

    Au-delà de la dernière ancre, prolonge la pente du dernier segment
    (résultat borné à [0, 100]).
    """
    ages = [a for a, _ in cohort_data]
    pcts = [p for _, p in cohort_data]
    if age <= ages[0]:
        return float(pcts[0])
    if age > ages[-1]:
        if len(ages) >= 2:
            slope = (pcts[-1] - pcts[-2]) / (ages[-1] - ages[-2])
        else:
            slope = 0.0
        return max(0.0, min(100.0, pcts[-1] + slope * (age - ages[-1])))
    for i in range(1, len(ages)):
        if age <= ages[i]:
            a0, a1 = ages[i - 1], ages[i]
            p0, p1 = pcts[i - 1], pcts[i]
            return p0 + (p1 - p0) * (age - a0) / (a1 - a0)
    return float(pcts[-1])


def get_cohort_survival(sex: str, birth_year: int, age: float) -> float:
    """
    Retourne % vivants pour une cohorte et un âge.
    Interpole entre les deux cohortes de référence les plus proches.
    """
    data = COHORT_SURVIVAL[sex]
    anchor_years = sorted(data.keys())
    if birth_year <= anchor_years[0]:
        return interp_survival(data[anchor_years[0]], age)
    if birth_year >= anchor_years[-1]:
        return interp_survival(data[anchor_years[-1]], age)
    lo = max(y for y in anchor_years if y <= birth_year)
    hi = min(y for y in anchor_years if y >= birth_year)
    p_lo = interp_survival(data[lo], age)
    if hi == lo:
        return p_lo
    p_hi = interp_survival(data[hi], age)
    w = (birth_year - lo) / (hi - lo)
    return p_lo + (p_hi - p_lo) * w
