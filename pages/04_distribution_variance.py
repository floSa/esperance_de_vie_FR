import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from common import (
    COLOR_E0,
    SEX_COLORS,
    SEX_LABELS,
    SEX_ZONES,
    apply_layout,
    download_csv,
    note_lecture,
    persist,
    render_sidebar,
    source_note,
)
from data import repository as repo
from data.repository import PREMIERE_ANNEE_MESUREE

st.set_page_config(page_title="Distribution & variance · Espérance de vie", page_icon="📐", layout="wide")
render_sidebar()

st.title("📐 Distribution des âges au décès — Compression de la mortalité")

persist("sexe", "femmes")
col_sexe, _ = st.columns([1, 3])
with col_sexe:
    sexe = st.selectbox(
        "Sexe", ["femmes", "hommes"],
        format_func=lambda s: SEX_LABELS[s], key="sexe",
    )

toutes = repo.distribution_deces()
df = toutes[toutes["sexe"] == sexe].reset_index(drop=True)
main_color = SEX_COLORS[sexe]
zone_color = SEX_ZONES[sexe]

# ---------------------------------------------------------------------------
# 1. Bande Q1–Q3, médiane et e0
# ---------------------------------------------------------------------------

fig = go.Figure()
fig.add_trace(go.Scatter(
    x=df["year"], y=df["q1"],
    line=dict(width=0), showlegend=False, hoverinfo="skip",
))
fig.add_trace(go.Scatter(
    x=df["year"], y=df["q3"],
    fill="tonexty", fillcolor=zone_color, line=dict(width=0),
    name="Moitié centrale des décès (Q1–Q3)",
    hovertemplate="Q3 : %{y:.0f} ans<extra></extra>",
))
fig.add_trace(go.Scatter(
    x=df["year"], y=df["median"],
    line=dict(color=main_color, width=3), name="Âge médian au décès",
    hovertemplate="Médiane : %{y:.0f} ans<extra></extra>",
))
fig.add_trace(go.Scatter(
    x=df["year"], y=df["e0"],
    line=dict(color=COLOR_E0, width=2, dash="dash"), name="Espérance de vie e₀",
    hovertemplate="e₀ : %{y:.1f} ans<extra></extra>",
))
fig.add_vline(
    x=PREMIERE_ANNEE_MESUREE, line_dash="dot", line_color="gray", opacity=0.6,
    annotation_text="↓ mesuré", annotation_position="top right",
)
fig.update_yaxes(range=[0, 100], title="Âge (ans)")
fig.update_xaxes(title="Année")
apply_layout(fig, height=520, legend=dict(orientation="h", yanchor="bottom", y=1.08, x=0),
             title=f"Distribution des âges au décès — {SEX_LABELS[sexe]}")
st.plotly_chart(fig, width='stretch')

ecart_median_e0 = float(df["median"].iloc[-1] - df["e0"].iloc[-1])
note_lecture(
    "La bande colorée contient la <strong>moitié centrale des décès</strong> : un "
    "quart survient avant son bord inférieur, un quart après son bord supérieur. "
    "Le trait plein est l'âge médian au décès, le tiret orange l'espérance de vie. "
    "<br><br>Le point le plus contre-intuitif est que la médiane passe "
    f"<strong>au-dessus</strong> de l'espérance de vie — {ecart_median_e0:.0f} ans "
    "d'écart aujourd'hui. Les deux ne mesurent pas la même chose : l'espérance de "
    "vie est une <em>moyenne</em>, tirée vers le bas par chaque décès précoce, "
    "tandis que la médiane est l'âge qui coupe les décès en deux. En 1900, la "
    "mortalité infantile massive écrasait la moyenne bien plus que la médiane. "
    "<br><br>À gauche du trait pointillé, les valeurs sont des estimations "
    "historiques ; à droite, elles sont calculées sur la distribution réelle des "
    "décès publiée par Eurostat.",
    f"{repo.millesime('distribution_deces_eurostat')} · estimations historiques "
    "avant " + str(PREMIERE_ANNEE_MESUREE),
)

# ---------------------------------------------------------------------------
# 2. Évolution de l'écart interquartile
# ---------------------------------------------------------------------------

iqr_debut, iqr_fin = float(df["iqr"].iloc[0]), float(df["iqr"].iloc[-1])
an_debut, an_fin = int(df["year"].iloc[0]), int(df["year"].iloc[-1])

fig_iqr = px.area(df, x="year", y="iqr",
                  labels={"year": "Année", "iqr": "Q3 − Q1 (ans)"})
fig_iqr.update_traces(line_color=main_color, fillcolor=zone_color, line_width=2,
                      hovertemplate="%{x} : %{y:.0f} ans<extra></extra>")
fig_iqr.add_annotation(x=an_debut, y=iqr_debut, text=f"<b>{iqr_debut:.0f} ans</b>",
                       showarrow=False, yshift=14, xshift=20,
                       font=dict(color=main_color, size=14))
fig_iqr.add_annotation(x=an_fin, y=iqr_fin, text=f"<b>{iqr_fin:.0f} ans</b>",
                       showarrow=False, yshift=14, xshift=-16,
                       font=dict(color=main_color, size=14))
apply_layout(fig_iqr, height=320,
             title="Écart interquartile — largeur de la fenêtre où l'on meurt")
st.plotly_chart(fig_iqr, width='stretch')

note_lecture(
    "Cette courbe est la <strong>hauteur de la bande précédente</strong>, année par "
    "année : le nombre d'années qui sépare le premier du dernier quart des décès. "
    "Plus elle descend, plus les décès se concentrent dans une tranche d'âge "
    f"étroite. Elle passe de <strong>{iqr_debut:.0f} ans en {an_debut}</strong> à "
    f"<strong>{iqr_fin:.0f} ans en {an_fin}</strong> chez les "
    f"{SEX_LABELS[sexe].lower()}. <br><br>C'est ce qu'on appelle la "
    "<strong>compression de la mortalité</strong> : en 1900, mourir à 5 ans ou à "
    "75 ans était également banal ; aujourd'hui la mort est devenue un événement "
    "de la vieillesse, prévisible à une dizaine d'années près.",
    repo.millesime("distribution_deces_eurostat"),
)

download_csv(df, "distribution_variance")
source_note()
