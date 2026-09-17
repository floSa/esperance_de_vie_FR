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
    fr_num,
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
    name="Moitié centrale des décès",
    hovertemplate="Q3 : %{y:.0f} ans<extra></extra>",
))
fig.add_trace(go.Scatter(
    x=df["year"], y=df["median"],
    line=dict(color=main_color, width=3), name="Âge médian au décès",
    hovertemplate="Médiane : %{y:.0f} ans<extra></extra>",
))
fig.add_trace(go.Scatter(
    x=df["year"], y=df["e0"],
    line=dict(color=COLOR_E0, width=2, dash="dash"),
    name="Espérance de vie à la naissance (moyenne)",
    hovertemplate="Espérance de vie : %{y:.1f} ans<extra></extra>",
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


# Année d'illustration : assez ancienne pour que l'écart moyenne / médiane
# saute aux yeux, ce qui est précisément le point difficile du graphique.
AN_EXEMPLE = 1920
ligne_ex = df[df["year"] == AN_EXEMPLE]
ligne_ex = ligne_ex.iloc[0] if len(ligne_ex) else df.iloc[0]
an_exemple = int(ligne_ex["year"])
med_ex = float(ligne_ex["median"])
q1_ex, q3_ex = float(ligne_ex["q1"]), float(ligne_ex["q3"])
e0_ex = float(ligne_ex["e0"])

note_lecture(
    "<strong>Année</strong> : conditions de mortalité de l'année, et non génération "
    "née cette année-là. La valeur de 1920 décrit les âges au décès d'une vie "
    "entière soumise à la mortalité de 1920."
    "<br><br>"
    f"<strong>{SEX_LABELS[sexe]}, {an_exemple} :</strong>"
    "<br>"
    f"Trait plein : âge médian, {med_ex:.0f} ans. La moitié des décès survient "
    "avant, la moitié après."
    "<br>"
    f"Bande : de {q1_ex:.0f} à {q3_ex:.0f} ans, moitié centrale des décès. Un quart "
    f"des décès avant {q1_ex:.0f} ans, un quart après {q3_ex:.0f} ans."
    "<br>"
    f"Tiret orange : espérance de vie à la naissance, {fr_num(e0_ex)} ans, soit "
    "l'âge moyen au décès."
    "<br><br>"
    f"<strong>Moyenne ({fr_num(e0_ex)}) inférieure à la médiane ({med_ex:.0f})</strong> : "
    f"effet de la mortalité infantile de {an_exemple}, le bord bas de la bande étant "
    f"à {q1_ex:.0f} ans. Les décès d'enfants abaissent la moyenne, pas la médiane."
    "<br><br>"
    "<strong>Évolution</strong> : bande en hausse et de plus en plus étroite. Les "
    "décès surviennent à des âges plus élevés et plus concentrés."
    "<br><br>"
    f"<strong>Trait vertical, {PREMIERE_ANNEE_MESUREE}</strong> : estimations "
    "historiques à gauche, décès publiés par Eurostat à droite.",
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
    "<strong>Axe horizontal</strong> : années, "
    f"de {an_debut} à {an_fin}."
    "<br>"
    "<strong>Axe vertical</strong> : écart interquartile, en années."
    "<br>"
    "<strong>Courbe</strong> : hauteur de la bande du graphique précédent, soit la "
    "largeur de la tranche d'âge contenant la moitié centrale des décès."
    "<br><br>"
    "Courbe en baisse : décès concentrés dans une tranche d'âge plus étroite."
    "<br>"
    f"{SEX_LABELS[sexe]} : <strong>{iqr_debut:.0f} ans en {an_debut}</strong>, "
    f"<strong>{iqr_fin:.0f} ans en {an_fin}</strong>."
    "<br><br>"
    "<strong>Compression de la mortalité</strong> : décès dispersés de l'enfance à la "
    "vieillesse en 1900, concentrés aux âges élevés aujourd'hui.",
    repo.millesime("distribution_deces_eurostat"),
)

download_csv(df, "distribution_variance")
source_note()
