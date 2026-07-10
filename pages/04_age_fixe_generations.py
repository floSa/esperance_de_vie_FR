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
    persist,
    render_sidebar,
    source_note,
)

st.set_page_config(page_title="Âge fixe × générations · Espérance de vie", page_icon="🔄", layout="wide")
render_sidebar()

st.title("🔄 Survie à un âge donné — comparaison entre générations")
st.caption(
    f"Question posée : *« Les personnes de 70 ans en {CURRENT_YEAR} ont-elles "
    "survécu plus que les personnes de 70 ans en 2000 ? »*"
)

# ---------------------------------------------------------------------------
# 1. Sélecteurs
# ---------------------------------------------------------------------------

persist("sexe", "femmes")
persist("age_fixe", 70)

col_sexe, col_age = st.columns([1, 3])
with col_sexe:
    sexe = st.radio(
        "Sexe", ["femmes", "hommes"], format_func=lambda s: SEX_LABELS[s],
        horizontal=True, key="sexe",
    )
with col_age:
    age = st.select_slider(
        "Âge observé", options=[35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 85, 90],
        key="age_fixe",
    )

# ---------------------------------------------------------------------------
# 2. Série : % de vivants à `age` ans, par année calendaire
# ---------------------------------------------------------------------------


@st.cache_data
def build_fixed_age_series(sexe: str, age: int) -> pd.DataFrame:
    y_min = 1930 + age
    y_max = min(CURRENT_YEAR, 1990 + age)
    rows = []
    for year in range(y_min, y_max + 1):
        birth = year - age
        rows.append({
            "annee": year,
            "naissance": birth,
            "vivants_pct": get_cohort_survival(sexe, birth, age),
        })
    df = pd.DataFrame(rows)
    df["decedes_pct"] = 100 - df["vivants_pct"]
    return df


df = build_fixed_age_series(sexe, age)
y_min, y_max = int(df["annee"].iloc[0]), int(df["annee"].iloc[-1])
pct_debut, pct_fin = float(df["vivants_pct"].iloc[0]), float(df["vivants_pct"].iloc[-1])
gain = pct_fin - pct_debut

st.markdown(
    f"> En **{y_min}**, les **{age} ans** (nés en {y_min - age}) avaient "
    f"**{fr_num(pct_debut)} %** encore en vie. En **{y_max}** (nés en "
    f"{y_max - age}) : **{fr_num(pct_fin)} %**. Soit **+{fr_num(gain)} points** "
    "de pourcentage."
)

# ---------------------------------------------------------------------------
# 3. Métriques
# ---------------------------------------------------------------------------

c1, c2, c3, c4 = st.columns(4)
c1.metric(f"% en vie en {y_min}", f"{fr_num(pct_debut)} %")
c2.metric(f"% en vie en {y_max}", f"{fr_num(pct_fin)} %")
c3.metric("Progression absolue", f"+{fr_num(gain)} pts")
c4.metric("Cohortes couvertes", f"{y_min - age} → {y_max - age}")

# ---------------------------------------------------------------------------
# 4. Graphique
# ---------------------------------------------------------------------------

y_axis_min = max(0.0, float(df["vivants_pct"].min()) - 5)

fig = go.Figure()
fig.add_trace(go.Scatter(
    x=df["annee"], y=df["vivants_pct"],
    fill="tozeroy", fillcolor=SEX_ZONES[sexe],
    line=dict(color=SEX_COLORS[sexe], width=2.5),
    name=f"Encore en vie à {age} ans",
    hovertemplate="%{x} (nés en %{customdata}) : %{y:.1f} % en vie<extra></extra>",
    customdata=df["naissance"],
))
fig.add_trace(go.Scatter(
    x=df["annee"], y=[100] * len(df),
    fill="tonexty", fillcolor=COLOR_DECEDES,
    line=dict(width=0),
    name=f"Décédés avant {age} ans",
    customdata=df["decedes_pct"],
    hovertemplate="%{x} : %{customdata:.1f} % décédés<extra></extra>",
))
if y_max >= CURRENT_YEAR:
    fig.add_vline(
        x=CURRENT_YEAR, line_dash="dash", line_color="gray",
        annotation_text=str(CURRENT_YEAR), annotation_position="top left",
    )
fig.add_annotation(
    x=y_max, y=pct_fin, ax=y_min, ay=pct_debut,
    axref="x", ayref="y",
    text=f"<b>+{fr_num(gain)} pts</b>",
    showarrow=True, arrowhead=3, arrowwidth=2,
    arrowcolor=SEX_COLORS[sexe],
    font=dict(color=SEX_COLORS[sexe], size=14),
)
fig.update_yaxes(range=[y_axis_min, 100.5], title=f"% de la cohorte en vie à {age} ans")
fig.update_xaxes(title="Année calendaire")
apply_layout(
    fig, height=520,
    legend=dict(orientation="h", yanchor="bottom", y=1.05, x=0),
    title=f"{SEX_LABELS[sexe]} — part de la génération encore en vie à {age} ans, "
          f"selon l'année d'observation",
)
st.plotly_chart(fig, use_container_width=True)

st.caption(
    "Lecture : chaque point compare des **générations différentes** au même âge. "
    "La hausse traduit la baisse de la mortalité prématurée (infantile, "
    "tuberculose, guerres, accidents) au fil des cohortes."
)

download_csv(df, "age_fixe_generations")
source_note()
