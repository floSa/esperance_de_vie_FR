import plotly.graph_objects as go
import streamlit as st

from common import (
    COLOR_E0,
    COLOR_FEMMES,
    COLOR_HOMMES,
    apply_layout,
    download_csv,
    fr_num,
    note_lecture,
    render_sidebar,
    source_note,
)
from data import repository as repo

st.set_page_config(page_title="Vue générale · Espérance de vie", page_icon="📈", layout="wide")
render_sidebar()

# Une seule question sur cette page : comment l'espérance de vie à la naissance
# a-t-elle évolué chez les femmes et chez les hommes. Une source, une période.
serie = repo.serie_par_sexe(0, source="insee")
an_debut, an_fin = int(serie["year"].iloc[0]), int(serie["year"].iloc[-1])
premiere, derniere = serie.iloc[0], serie.iloc[-1]

st.title("📈 Vue générale — évolution de l'espérance de vie")
st.caption(
    f"Espérance de vie à la naissance en France, femmes et hommes, "
    f"de {an_debut} à {an_fin}."
)

# ---------------------------------------------------------------------------
# 1. Chiffres clés
# ---------------------------------------------------------------------------

c1, c2, c3, c4 = st.columns(4)
c1.metric(f"Femmes, {an_fin}", f"{fr_num(derniere['femmes'])} ans",
          delta=f"+{fr_num(derniere['femmes'] - premiere['femmes'])} ans depuis {an_debut}")
c2.metric(f"Hommes, {an_fin}", f"{fr_num(derniere['hommes'])} ans",
          delta=f"+{fr_num(derniere['hommes'] - premiere['hommes'])} ans depuis {an_debut}")
c3.metric("Écart femmes − hommes",
          f"{fr_num(derniere['femmes'] - derniere['hommes'])} ans",
          delta=f"{fr_num(derniere['femmes'] - derniere['hommes'] - (premiere['femmes'] - premiere['hommes']))} ans depuis {an_debut}",
          delta_color="off", delta_arrow="off")
c4.metric("Années couvertes", f"{an_debut} → {an_fin}")

# ---------------------------------------------------------------------------
# 2. Évolution 1946 → aujourd'hui
# ---------------------------------------------------------------------------

fig = go.Figure()
for sexe, couleur in (("femmes", COLOR_FEMMES), ("hommes", COLOR_HOMMES)):
    fig.add_trace(go.Scatter(
        x=serie["year"], y=serie[sexe],
        line=dict(color=couleur, width=2.5),
        name=sexe.capitalize(),
        hovertemplate="%{x} : %{y:.1f} ans<extra>" + sexe + "</extra>",
    ))
fig.update_yaxes(title="Espérance de vie à la naissance (ans)")
fig.update_xaxes(title="Année")
apply_layout(fig, height=460,
             legend=dict(orientation="h", yanchor="bottom", y=1.06, x=0),
             title=f"France, {an_debut}–{an_fin}")
st.plotly_chart(fig, width='stretch')

note_lecture(
    "<strong>Axe horizontal</strong> : années, "
    f"de {an_debut} à {an_fin}."
    "<br>"
    "<strong>Axe vertical</strong> : nombre d'années que vivrait un nouveau-né de "
    "l'année si la mortalité restait constante."
    "<br>"
    "<strong>Courbes</strong> : femmes en rose, hommes en bleu."
    "<br><br>"
    "Progression continue sur toute la période. Gain de "
    f"<strong>{fr_num(derniere['femmes'] - premiere['femmes'])} ans</strong> "
    f"pour les femmes depuis {an_debut}, "
    f"<strong>{fr_num(derniere['hommes'] - premiere['hommes'])} ans</strong> "
    "pour les hommes."
    "<br><br>"
    "Écart entre les courbes : <strong>surmortalité masculine</strong>, en hausse "
    "jusqu'aux années 1990, en baisse depuis.",
    repo.millesime("esperance_vie_fr_insee"),
)

# ---------------------------------------------------------------------------
# 3. Recul historique
# ---------------------------------------------------------------------------

st.subheader("Série longue, 1816–2023")

longue = repo.esperance_vie_longue()
fig_longue = go.Figure()
fig_longue.add_trace(go.Scatter(
    x=longue["year"], y=longue["esperance"],
    line=dict(color=COLOR_E0, width=2),
    hovertemplate="%{x} : %{y:.1f} ans<extra></extra>",
))
for an, txt in ((1871, "1871"), (1918, "1918"), (1940, "1940")):
    fig_longue.add_vline(x=an, line_dash="dot", line_color="gray", opacity=0.5)
    fig_longue.add_annotation(x=an, y=1.05, yref="paper", text=txt,
                              showarrow=False, font=dict(size=11))
fig_longue.update_yaxes(title="Espérance de vie à la naissance (ans)")
fig_longue.update_xaxes(title="Année")
apply_layout(fig_longue, height=360, showlegend=False,
             title="France, 1816–2023, femmes et hommes réunis")
st.plotly_chart(fig_longue, width='stretch')

note_lecture(
    "Même indicateur que le graphique précédent, sur deux siècles."
    "<br>"
    "<strong>Courbe unique</strong> : femmes et hommes réunis, le détail par sexe "
    "n'étant pas disponible avant 1946."
    "<br><br>"
    "Creux : crises de mortalité."
    "<br>"
    "1871 : guerre franco-prussienne. 1918 : grippe espagnole et fin de la "
    "Première Guerre. 1940 : Seconde Guerre."
    "<br><br>"
    "1918 : <strong>34,8 ans</strong>, contre 43,0 en 1917, puis remontée dès "
    "1919. L'indicateur décrit la mortalité d'une année, et non la durée d'une vie.",
    repo.millesime("esperance_vie_fr_longue_owid"),
)

download_csv(serie, "vue_generale")
source_note()
