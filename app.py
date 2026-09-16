import streamlit as st

from common import fr_num, render_sidebar, source_note
from data import repository as repo

st.set_page_config(
    page_title="Espérance de vie · France & Europe",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

render_sidebar()

serie = repo.serie_par_sexe(0)
annee = int(serie["year"].max())
derniere = serie.iloc[-1]

st.title("📊 Espérance de vie — France & Europe")
st.markdown(
    "Quatre vues d'analyse de l'espérance de vie en France et en Europe, "
    "construites à partir des séries longues de l'**INSEE**, des tables de "
    "mortalité **Eurostat** et des séries historiques d'**Our World in Data**."
)

c1, c2, c3 = st.columns(3)
c1.metric(f"e₀ femmes ({annee})", f"{fr_num(derniere['femmes'])} ans")
c2.metric(f"e₀ hommes ({annee})", f"{fr_num(derniere['hommes'])} ans")
c3.metric("Écart femmes − hommes",
          f"{fr_num(derniere['femmes'] - derniere['hommes'])} ans")

st.markdown("---")
st.subheader("Les quatre vues")

col_a, col_b = st.columns(2)
with col_a:
    st.page_link(
        "pages/01_vue_generale.py",
        label="**Vue générale** — évolution 1900–2025 et comparaison européenne",
        icon="📈",
    )
    st.page_link(
        "pages/02_distribution_variance.py",
        label="**Distribution & variance** — compression de la mortalité (Q1–Q3)",
        icon="📐",
    )
with col_b:
    st.page_link(
        "pages/03_explorateur_cohorte.py",
        label="**Explorateur de cohorte** — qui est encore en vie ?",
        icon="👥",
    )
    st.page_link(
        "pages/04_survie_age_donne.py",
        label="**Survie à un âge donné** — comparaison entre générations",
        icon="🔄",
    )

st.markdown("")
st.info(
    "Les données sont **régénérées depuis les API publiques** (INSEE Melodi, "
    "Eurostat, Our World in Data) par `scripts/refresh_data.py`. La provenance "
    "de chaque jeu — URL, paramètres, millésime, date d'extraction — est "
    "consignée dans `data/sources/manifest.json`.\n\n"
    "Seule la survie **par génération** reste une estimation : aucune source "
    "ouverte ne publie de tables de mortalité par cohorte pour la France."
)

source_note()
