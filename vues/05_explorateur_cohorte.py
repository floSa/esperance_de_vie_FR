import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from common import (
    COLOR_DECEDES,
    COLOR_VIVANTS_ZONE,
    CURRENT_YEAR,
    SEX_COLORS,
    SEX_LABELS,
    age_max_documente,
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

st.title("👥 Explorateur de cohorte — survie par génération")

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
# Les générations les plus anciennes ont dépassé le dernier âge documenté :
# on s'arrête à ce que les données disent, plutôt que d'extrapoler.
age_donnees = min(age_actuel, age_max_documente(sexe))
donnees_tronquees = age_donnees < age_actuel

# ---------------------------------------------------------------------------
# 2. Métriques
# ---------------------------------------------------------------------------

naissances = repo.naissances()[annee_naissance] * SEX_RATIO[sexe]
pct_vivants = get_cohort_survival(sexe, annee_naissance, age_donnees)
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
c3.metric(f"Encore en vie à {age_donnees} ans", f"{fr_num(vivants, 0)}",
          delta=f"{fr_num(pct_vivants)} %", delta_color="off", delta_arrow="off")
c4.metric(f"Décédés avant {age_donnees} ans", f"{fr_num(decedes, 0)}",
          delta=f"{fr_num(100 - pct_vivants)} %", delta_color="off", delta_arrow="off")
c5.metric(
    "Décès moyen attendu vers",
    f"{fr_num(age_actuel + residuelle, 0)} ans",
    delta=f"+{fr_num(residuelle)} ans à vivre",
    delta_color="off", delta_arrow="off",
    help="Pour les survivants uniquement, selon la table du moment 2025",
)

if donnees_tronquees:
    st.caption(
        f"Âge de la génération en {CURRENT_YEAR} : **{age_actuel} ans**. Tables de "
        f"survie limitées à **{age_donnees} ans** : effectifs affichés à "
        f"{age_donnees} ans, dernier âge documenté."
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


curve = build_survival_curve(sexe, annee_naissance, age_donnees)

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
    x=age_donnees,
    line_dash="dash",
    line_color=SEX_COLORS[sexe],
    annotation_text=f"{age_donnees} ans",
    annotation_position="top left",
)
fig.update_yaxes(range=[0, 100], title="% de la cohorte")
fig.update_xaxes(range=[0, age_donnees], title="Âge")
apply_layout(
    fig, height=500,
    legend=dict(orientation="h", yanchor="bottom", y=1.05, x=0),
    title=f"Cohorte {SEX_LABELS[sexe].lower()} née en {annee_naissance} — "
          f"{fr_num(pct_vivants)} % encore en vie à {age_donnees} ans",
)
st.plotly_chart(fig, width='stretch')

note_lecture(
    f"<strong>Axe horizontal</strong> : âge de la génération née en "
    f"<strong>{annee_naissance}</strong>, de 0 à {age_donnees} ans."
    "<br>"
    "<strong>Axe vertical</strong> : part de la génération, en %."
    "<br>"
    "<strong>Zones</strong> : en gris, part encore en vie ; en rouge, part décédée. "
    "Total de 100 %."
    "<br><br>"
    "Forte pente initiale : <strong>mortalité infantile</strong>, concentrée avant "
    "le premier anniversaire. Zone rouge ensuite quasi stable pendant plusieurs "
    "décennies, puis en hausse à partir de 60 ans environ.",
    "Survie par génération : estimation à ±5 % (tables de génération INSEE / "
    "Vallin & Meslé) · effectifs de naissance : "
    + repo.millesime("naissances_fr_insee"),
)

st.warning(
    f"**Âge de décès attendu ({fr_num(age_actuel + residuelle, 0)} ans) supérieur à "
    "l'espérance de vie à la naissance** : valeur limitée aux **survivants**, les "
    f"{fr_num(100 - pct_vivants)} % de la génération déjà décédés n'étant pas "
    "comptés. L'âge de décès attendu augmente avec l'âge atteint.\n\n"
    "Calcul fondé sur la **table du moment 2025**, à conditions sanitaires "
    "constantes. En cas de poursuite des progrès, la survie réelle de la génération "
    "sera **supérieure**."
)

download_csv(curve, "cohorte_explorer")
source_note()
