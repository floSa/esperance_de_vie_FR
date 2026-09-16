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
    "<strong>Une année n'est pas une génération.</strong> Elle désigne les "
    "conditions de mortalité de cette année-là. Lire 1920, c'est répondre à : "
    "« si toute une vie se déroulait avec la mortalité de 1920, à quel âge "
    "mourrait-on ? »"
    "<br><br>"
    f"<strong>Exemple, {SEX_LABELS[sexe].lower()} en {an_exemple} :</strong>"
    "<br>"
    f"Le trait plein est à {med_ex:.0f} ans. C'est l'âge médian : la moitié "
    f"meurt avant {med_ex:.0f} ans, la moitié après."
    "<br>"
    f"La bande va de {q1_ex:.0f} à {q3_ex:.0f} ans. C'est là que meurent les "
    f"50 % du milieu. Un quart meurt avant {q1_ex:.0f} ans, un quart après "
    f"{q3_ex:.0f} ans."
    "<br>"
    f"Le tiret orange est à {fr_num(e0_ex)} ans. C'est l'espérance de vie à la "
    "naissance, autrement dit la moyenne."
    "<br><br>"
    f"<strong>Pourquoi la moyenne ({fr_num(e0_ex)}) est-elle plus basse que la "
    f"médiane ({med_ex:.0f}) ?</strong> Parce qu'en {an_exemple} beaucoup "
    f"d'enfants mouraient — le bord bas de la bande est à {q1_ex:.0f} ans. "
    "Chaque mort d'enfant tire la moyenne vers le bas, pas la médiane."
    "<br><br>"
    "<strong>Ce que raconte le graphique de gauche à droite :</strong> la "
    "bande monte et se resserre. On meurt de plus en plus vieux, et dans une "
    "fourchette d'âge de plus en plus étroite."
    "<br><br>"
    f"<strong>Le trait vertical de {PREMIERE_ANNEE_MESUREE}</strong> sépare "
    "les estimations historiques (à gauche) des décès réellement publiés par "
    "Eurostat (à droite).",
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
    "<strong>Axe horizontal</strong> : les années, "
    f"de {an_debut} à {an_fin}."
    "<br>"
    "<strong>Axe vertical</strong> : un nombre d'années."
    "<br>"
    "<strong>Une seule courbe</strong> : la hauteur de la bande du graphique "
    "précédent."
    "<br><br>"
    "Cette hauteur est la largeur de la fenêtre d'âge où se concentre la "
    "moitié des décès."
    "<br>"
    "Quand la courbe descend, cette fenêtre se resserre. On meurt dans une "
    "tranche d'âge de plus en plus étroite."
    "<br><br>"
    f"Chez les {SEX_LABELS[sexe].lower()}, elle passe de "
    f"<strong>{iqr_debut:.0f} ans en {an_debut}</strong> à "
    f"<strong>{iqr_fin:.0f} ans en {an_fin}</strong>."
    "<br><br>"
    "<strong>C'est la compression de la mortalité.</strong>"
    "<br>"
    "En 1900, mourir à 5 ans ou à 75 ans était également banal."
    "<br>"
    "Aujourd'hui, la mort est un événement de la vieillesse, prévisible à une "
    "dizaine d'années près.",
    repo.millesime("distribution_deces_eurostat"),
)

download_csv(df, "distribution_variance")
source_note()
