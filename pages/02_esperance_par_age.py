import plotly.graph_objects as go
import streamlit as st

from common import (
    COLOR_FEMMES,
    COLOR_HOMMES,
    apply_layout,
    download_csv,
    fr_num,
    note_lecture,
    persist,
    render_sidebar,
    source_note,
)
from data import repository as repo

st.set_page_config(page_title="Espérance de vie par âge · Espérance de vie",
                   page_icon="🎚️", layout="wide")
render_sidebar()

st.title("🎚️ Espérance de vie par âge")
st.caption(
    "Nombre moyen d'années restant à vivre selon l'âge atteint, et son évolution "
    "de 1998 à 2024."
)

# ---------------------------------------------------------------------------
# 1. Sélection de l'âge
# ---------------------------------------------------------------------------

# Eurostat uniquement : seule source couvrant les 96 âges. L'axe des années est
# fixé à sa période complète, pour que deux âges restent comparables.
an_debut, an_fin = repo.periode_comparable()
persist("age_observe", 40)
age = st.select_slider(
    "Âge observé",
    options=repo.ages_disponibles(),
    format_func=lambda a: "à la naissance" if a == 0 else f"{a} ans",
    key="age_observe",
)
libelle_age = "à la naissance" if age == 0 else f"{age} ans"
serie = repo.serie_par_sexe(age, source="eurostat")
premiere, derniere = serie.iloc[0], serie.iloc[-1]
an_premier = int(premiere["year"])

# ---------------------------------------------------------------------------
# 2. Chiffres clés
# ---------------------------------------------------------------------------

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Âge observé", "Naissance" if age == 0 else f"{age} ans")
c2.metric(f"Femmes, {an_fin}", f"{fr_num(derniere['femmes'])} ans")
c3.metric(f"Hommes, {an_fin}", f"{fr_num(derniere['hommes'])} ans")
c4.metric("Écart femmes − hommes",
          f"{fr_num(derniere['femmes'] - derniere['hommes'])} ans")
c5.metric(f"Gain femmes depuis {an_premier}",
          f"+{fr_num(derniere['femmes'] - premiere['femmes'])} ans")

if age == 0:
    st.caption(
        f"{an_fin} : espérance de vie à la naissance de **{fr_num(derniere['femmes'])} "
        f"ans** pour les femmes, **{fr_num(derniere['hommes'])} ans** pour les hommes."
    )
else:
    st.caption(
        f"{an_fin} : femmes de {age} ans, **{fr_num(derniere['femmes'])} années** "
        f"restant à vivre en moyenne, soit un décès vers "
        f"**{fr_num(age + derniere['femmes'], 0)} ans**."
    )

# ---------------------------------------------------------------------------
# 3. Évolution
# ---------------------------------------------------------------------------

fig = go.Figure()
for sexe, couleur in (("femmes", COLOR_FEMMES), ("hommes", COLOR_HOMMES)):
    fig.add_trace(go.Scatter(
        x=serie["year"], y=serie[sexe],
        line=dict(color=couleur, width=2.5),
        name=sexe.capitalize(),
        hovertemplate="%{x} : %{y:.1f} ans<extra>" + sexe + "</extra>",
    ))
fig.update_yaxes(title=("Espérance de vie à la naissance (ans)" if age == 0
                       else f"Années restant à vivre à {age} ans"))
fig.update_xaxes(title="Année", range=[an_debut - 1, an_fin + 1])
apply_layout(fig, height=440,
             legend=dict(orientation="h", yanchor="bottom", y=1.06, x=0),
             title=f"Espérance de vie {libelle_age} — {an_debut} à {an_fin}")
st.plotly_chart(fig, width='stretch')

exemple = round(float(derniere["femmes"]))
if age == 0:
    axe_y = ("nombre d'années que vivrait un nouveau-né de l'année si la "
             "mortalité restait constante.")
    piege = "Indicateur de la mortalité de l'année, et non prévision."
else:
    axe_y = f"nombre moyen d'années restant à vivre à {age} ans, l'année considérée."
    piege = (f"Valeur exprimée en durée, et non en âge : un point à {exemple} "
             f"correspond à {exemple} années restant à vivre, soit un décès vers "
             f"{age + exemple} ans."
             "<br>"
             f"Calcul limité aux personnes en vie à {age} ans.")

note_lecture(
    "<strong>Axe horizontal</strong> : années, "
    f"de {an_debut} à {an_fin}, identiques pour tous les âges sélectionnés."
    "<br>"
    "<strong>Axe vertical</strong> : " + axe_y
    + "<br>"
    "<strong>Courbes</strong> : femmes en rose, hommes en bleu."
    "<br><br>"
    + piege
    + (
        f"<br><br>Âge publié par Eurostat à partir de {an_premier} : début de courbe "
        "décalé, axe inchangé."
        if an_premier > an_debut else ""
    ),
    repo.millesime("esperance_vie_fr_tous_ages_eurostat"),
)

download_csv(serie, f"esperance_age_{age}")
source_note()
