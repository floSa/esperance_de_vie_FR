import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from common import (
    COLOR_DECEDES,
    COLOR_VIVANTS_ZONE,
    CURRENT_YEAR,
    SEX_COLORS,
    SEX_LABELS,
    apply_layout,
    download_csv,
    fr_num,
    get_cohort_survival,
    interp_survival,
    note_lecture,
    persist,
    render_sidebar,
    source_note,
)
from data import repository as repo
from data.embedded import RESIDUAL_LIFE_2025, SEX_RATIO

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

naissances = repo.naissances()[annee_naissance] * SEX_RATIO[sexe]
pct_vivants = get_cohort_survival(sexe, annee_naissance, age_actuel)
vivants = naissances * pct_vivants / 100
decedes = naissances - vivants
residuelle = interp_survival(
    sorted(RESIDUAL_LIFE_2025[sexe].items()), min(age_actuel, 95)
)

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric(
    f"Génération {annee_naissance}",
    f"{age_actuel} ans",
    help=f"Âge atteint en {CURRENT_YEAR}",
)
c2.metric(
    f"Nés en {annee_naissance} ({SEX_LABELS[sexe].lower()})",
    f"{fr_num(naissances, 0)}",
    help="Naissances vivantes France métropolitaine (INSEE), "
         "réparties selon la proportion de filles et de garçons à la naissance",
)
c3.metric("Encore en vie estimés", f"{fr_num(vivants, 0)}",
          delta=f"{fr_num(pct_vivants)} %")
c4.metric("Décédés estimés", f"{fr_num(decedes, 0)}",
          delta=f"-{fr_num(100 - pct_vivants)} %", delta_color="inverse")
c5.metric(
    "Décès moyen attendu vers",
    f"{fr_num(age_actuel + residuelle, 0)} ans",
    delta=f"+{fr_num(residuelle)} ans à vivre",
    delta_color="off",
    help="Pour les survivants uniquement, selon la table du moment 2025",
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
    fill="tonexty", fillcolor=COLOR_VIVANTS_ZONE,
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
st.plotly_chart(fig, width='stretch')

note_lecture(
    f"L'axe horizontal suit la génération née en <strong>{annee_naissance}</strong> "
    f"tout au long de sa vie, de 0 an jusqu'à son âge actuel "
    f"({age_actuel} ans). La zone colorée du haut est la part encore en vie, la "
    "zone rouge du bas la part déjà décédée — les deux font toujours 100 %. "
    "<br><br>La pente raide tout à gauche est la <strong>mortalité "
    "infantile</strong> : une part notable des décès d'une génération survient "
    "avant son premier anniversaire. La zone rouge reste ensuite presque plate "
    "pendant des décennies, puis s'élargit à partir de 60 ans environ.",
    "Survie par génération : estimation à ±5 % (tables de génération INSEE / "
    "Vallin & Meslé) · effectifs de naissance : "
    + repo.millesime("naissances_fr_insee"),
)

st.warning(
    f"**Pourquoi « décès vers {fr_num(age_actuel + residuelle, 0)} ans » dépasse "
    "l'espérance de vie à la naissance** — cette valeur ne concerne que les "
    f"**survivants** : les {fr_num(100 - pct_vivants)} % de la génération déjà "
    "décédés n'y comptent pas. Avoir atteint "
    f"{age_actuel} ans, c'est avoir échappé à la mortalité infantile, aux "
    "accidents et aux maladies précoces. Plus on avance en âge, plus l'âge de "
    "décès attendu recule.\n\n"
    "Le calcul repose de plus sur la **table du moment 2025**, qui fige les "
    "conditions sanitaires d'aujourd'hui. Si les progrès se poursuivent, la "
    "survie réelle de cette génération sera **supérieure** : les tables du moment "
    "sous-estiment historiquement la longévité des générations."
)

download_csv(curve, "cohorte_explorer")
source_note()
