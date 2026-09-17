import streamlit as st

# Navigation explicite : sans elle, Streamlit nomme les pages d'après leurs
# fichiers (« esperance par age »), sans majuscules ni accents.
st.set_page_config(
    page_title="Espérance de vie · France & Europe",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

PAGES = [
    st.Page("accueil.py", title="Accueil", icon="📊", default=True),
    st.Page("vues/01_vue_generale.py", title="Vue générale", icon="📈",
            url_path="vue_generale"),
    st.Page("vues/02_esperance_par_age.py", title="Espérance de vie par âge", icon="🎚️",
            url_path="esperance_par_age"),
    st.Page("vues/03_comparaison_europe.py", title="Comparaison européenne", icon="🇪🇺",
            url_path="comparaison_europe"),
    st.Page("vues/04_distribution_variance.py", title="Distribution et variance", icon="📐",
            url_path="distribution_variance"),
    st.Page("vues/05_explorateur_cohorte.py", title="Explorateur de cohorte", icon="👥",
            url_path="explorateur_cohorte"),
    st.Page("vues/06_survie_age_donne.py", title="Survie à un âge donné", icon="🔄",
            url_path="survie_age_donne"),
    st.Page("vues/07_personnalites.py", title="Personnalités", icon="🎭",
            url_path="personnalites"),
]

st.navigation(PAGES).run()
