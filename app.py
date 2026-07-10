import streamlit as st

from common import fr_num, render_sidebar, source_note
from data.embedded import PERIOD_DISTRIBUTION_FEMMES, PERIOD_DISTRIBUTION_HOMMES

st.set_page_config(
    page_title="Espérance de vie · France & Europe",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

render_sidebar()

st.title("📊 Espérance de vie — France & Europe")
st.markdown(
    "Quatre vues d'analyse de l'espérance de vie en France (1900–2025) et en "
    "Europe, construites à partir des tables de mortalité **HMD** (Human "
    "Mortality Database — base internationale des tables de mortalité), de "
    "l'**INSEE** et d'**Eurostat**."
)

f_last = PERIOD_DISTRIBUTION_FEMMES[-1]
h_last = PERIOD_DISTRIBUTION_HOMMES[-1]
c1, c2, c3 = st.columns(3)
c1.metric("e₀ femmes (2025)", f"{fr_num(f_last['e0'])} ans")
c2.metric("e₀ hommes (2025)", f"{fr_num(h_last['e0'])} ans")
c3.metric("Écart femmes − hommes", f"{fr_num(f_last['e0'] - h_last['e0'])} ans")

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
        "pages/03_cohorte_explorer.py",
        label="**Explorateur de cohorte** — qui est encore en vie ?",
        icon="👥",
    )
    st.page_link(
        "pages/04_age_fixe_generations.py",
        label="**Âge fixe × générations** — survie à un âge donné",
        icon="🔄",
    )

st.markdown("")
st.info(
    "Une partie des données est **embarquée** (approximations démographiques "
    "validées), une partie peut être **rafraîchie via API** : Eurostat "
    "(sans authentification) sur la page Vue générale, HMD (credentials "
    "`HMD_USER` / `HMD_PASSWORD` ou upload de fichier) sur la page "
    "Distribution & variance."
)

source_note()
