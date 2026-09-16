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

an_min, an_max = int(df["year"].iloc[0]), int(df["year"].iloc[-1])
med_fin = float(df["median"].iloc[-1])
e0_fin = float(df["e0"].iloc[-1])
ecart_median_e0 = med_fin - e0_fin
ecart_median_e0_debut = float(df["median"].iloc[0] - df["e0"].iloc[0])
q1_fin, q3_fin = float(df["q1"].iloc[-1]), float(df["q3"].iloc[-1])

note_lecture(
    "<strong>Axe horizontal</strong> : les années, "
    f"de {an_min} à {an_max}."
    "<br>"
    "<strong>Axe vertical</strong> : un âge, en années."
    "<br>"
    "<strong>Trois éléments</strong> : une bande colorée, un trait plein, un "
    "tiret orange."
    "<br><br>"
    "<strong>La bande</strong> contient la moitié des décès. Un quart a lieu "
    "avant son bord bas, un quart après son bord haut."
    f"<br>En {an_max} : de {q1_fin:.0f} à {q3_fin:.0f} ans."
    "<br><br>"
    "<strong>Le trait plein</strong> est l'âge médian au décès. La moitié des "
    f"gens meurent avant, la moitié après. En {an_max} : {med_fin:.0f} ans."
    "<br><br>"
    "<strong>Le tiret orange</strong> est l'espérance de vie. En "
    f"{an_max} : {fr_num(e0_fin)} ans."
    "<br><br>"
    "<strong>Regarde l'écart entre le trait plein et le tiret orange.</strong>"
    "<br>"
    f"En {an_min}, il était de {fr_num(ecart_median_e0_debut)} ans."
    f"<br>En {an_max}, il n'est plus que de {fr_num(ecart_median_e0)} an"
    f"{'s' if ecart_median_e0 >= 2 else ''}. Les deux se rejoignent."
    "<br><br>"
    "Les deux ne mesurent pas la même chose."
    "<br>"
    "L'espérance de vie est une moyenne. Chaque décès précoce la tire vers le "
    "bas."
    "<br>"
    "La médiane coupe les décès en deux. Un bébé mort à un an y compte pour "
    "une personne, pas pour 80 années perdues."
    "<br><br>"
    "En 1900, la mortalité infantile était massive : elle écrasait la moyenne "
    "bien plus que la médiane, d'où le grand écart."
    "<br>"
    "Aujourd'hui, presque plus personne ne meurt jeune. Les deux mesures "
    "convergent."
    "<br><br>"
    f"<strong>Le trait pointillé vertical, en {PREMIERE_ANNEE_MESUREE}</strong>, "
    "sépare deux régimes."
    "<br>"
    "À gauche : des estimations historiques."
    "<br>"
    "À droite : des valeurs calculées sur les décès réels publiés par Eurostat.",
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
