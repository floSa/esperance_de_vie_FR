import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from common import (
    COLOR_DECEDES,
    CURRENT_YEAR,
    SEX_COLORS,
    SEX_LABELS,
    SEX_ZONES,
    apply_layout,
    download_csv,
    fr_num,
    get_cohort_survival,
    interp_survival,
    persist,
    render_sidebar,
    source_note,
)
from data.embedded import BIRTHS_BY_YEAR, RESIDUAL_LIFE_2025, SEX_RATIO

st.set_page_config(page_title="Explorateur de cohorte · Espérance de vie", page_icon="👥", layout="wide")
render_sidebar()

st.title("👥 Explorateur de cohorte — Qui est encore en vie ?")

# ---------------------------------------------------------------------------
# 1. Sélecteurs
# ---------------------------------------------------------------------------

persist("sexe", "femmes")
persist("annee_naissance", 1960)

col_sexe, col_annee = st.columns([1, 3])
with col_sexe:
    sexe = st.selectbox(
        "Sexe", ["femmes", "hommes"], format_func=lambda s: SEX_LABELS[s], key="sexe"
    )
with col_annee:
    annee_naissance = st.slider("Année de naissance", 1930, 1990, key="annee_naissance")

age_actuel = CURRENT_YEAR - annee_naissance

# ---------------------------------------------------------------------------
# 2. Métriques
# ---------------------------------------------------------------------------

naissances = BIRTHS_BY_YEAR[annee_naissance] * SEX_RATIO[sexe]
pct_vivants = get_cohort_survival(sexe, annee_naissance, age_actuel)
vivants = naissances * pct_vivants / 100
decedes = naissances - vivants
residuelle = interp_survival(
    sorted(RESIDUAL_LIFE_2025[sexe].items()), min(age_actuel, 95)
)

c1, c2, c3, c4 = st.columns(4)
c1.metric(
    f"Nés en {annee_naissance} ({SEX_LABELS[sexe].lower()})",
    f"{fr_num(naissances, 0)}",
)
c2.metric(
    "Encore en vie estimés",
    f"{fr_num(vivants, 0)}",
    delta=f"{fr_num(pct_vivants)} %",
)
c3.metric(
    "Décédés estimés",
    f"{fr_num(decedes, 0)}",
    delta=f"-{fr_num(100 - pct_vivants)} %",
    delta_color="inverse",
)
c4.metric(
    f"Espérance résiduelle à {age_actuel} ans",
    f"{fr_num(residuelle)} ans",
    help="Table du moment 2025 (approx. INSEE/DREES)",
)

# ---------------------------------------------------------------------------
# 3. Courbe de survie
# ---------------------------------------------------------------------------


@st.cache_data
def build_survival_curve(sexe: str, annee_naissance: int, age_max: int) -> pd.DataFrame:
    ages = list(range(age_max + 1))
    vivants_pct = [get_cohort_survival(sexe, annee_naissance, a) for a in ages]
    return pd.DataFrame({
        "age": ages,
        "vivants_pct": vivants_pct,
        "decedes_pct": [100 - v for v in vivants_pct],
    })


curve = build_survival_curve(sexe, annee_naissance, age_actuel)

fig = go.Figure()
fig.add_trace(go.Scatter(
    x=curve["age"], y=curve["decedes_pct"],
    fill="tozeroy", fillcolor=COLOR_DECEDES,
    line=dict(color="rgba(248, 113, 113, 0.9)", width=2),
    name="Décédés (cumul)",
    hovertemplate="Âge %{x} : %{y:.1f} % décédés<extra></extra>",
))
fig.add_trace(go.Scatter(
    x=curve["age"], y=[100] * len(curve),
    fill="tonexty", fillcolor=SEX_ZONES[sexe],
    line=dict(width=0),
    name="Encore en vie",
    customdata=curve["vivants_pct"],
    hovertemplate="Âge %{x} : %{customdata:.1f} % en vie<extra></extra>",
))
fig.add_vline(
    x=age_actuel,
    line_dash="dash",
    line_color=SEX_COLORS[sexe],
    annotation_text=f"Âge en {CURRENT_YEAR} : {age_actuel} ans",
    annotation_position="top left",
)
fig.update_yaxes(range=[0, 100], title="% de la cohorte")
fig.update_xaxes(range=[0, age_actuel], title="Âge")
apply_layout(
    fig, height=500,
    legend=dict(orientation="h", yanchor="bottom", y=1.05, x=0),
    title=f"Cohorte {SEX_LABELS[sexe].lower()} née en {annee_naissance} — "
          f"{fr_num(pct_vivants)} % encore en vie à {age_actuel} ans",
)
st.plotly_chart(fig, use_container_width=True)

st.warning(
    "⚠️ **Espérance résiduelle** : la valeur affichée provient de la **table du "
    "moment 2025** (conditions de mortalité de 2025 figées). L'espérance réelle "
    "de la cohorte sera vraisemblablement **supérieure** si les progrès "
    "sanitaires se poursuivent — les tables du moment sous-estiment "
    "historiquement la survie des générations."
)

download_csv(curve, "cohorte_explorer")
source_note()
