import plotly.graph_objects as go
import streamlit as st

from common import (
    SEX_COLORS,
    SEX_LABELS,
    apply_layout,
    download_csv,
    fr_num,
    note_lecture,
    persist,
    render_sidebar,
    source_note,
)
from data import repository as repo
from data.repository import AGE_ADULTE, DonneesManquantes

st.set_page_config(page_title="Personnalités · Espérance de vie", page_icon="🎭", layout="wide")
render_sidebar()

st.title("🎭 Les personnalités vivent-elles plus longtemps ?")
st.caption(
    "Âge moyen au décès des personnalités françaises, comparé à celui de "
    "l'ensemble des Français morts la même période."
)

persist("sexe", "femmes")
col_sexe, _ = st.columns([1, 3])
with col_sexe:
    sexe = st.selectbox(
        "Sexe", ["femmes", "hommes"],
        format_func=lambda s: SEX_LABELS[s], key="sexe",
    )

try:
    periodes = repo.comparaison_age_deces(sexe)
    bilan = repo.bilan_age_deces(sexe)
except DonneesManquantes as e:
    st.error(
        f"Données manquantes : {e}\n\nLa liste des personnalités vient du projet "
        "`deces_personnalites_FR`. Lancez sa collecte, puis "
        "`uv run python -m scripts.refresh_data` dans ce projet."
    )
    st.stop()

population = "Ensemble des Françaises" if sexe == "femmes" else "Ensemble des Français"
tous = "toutes les Françaises mortes" if sexe == "femmes" else "tous les Français morts"
# « ensemble des Français » : minuscule sur « ensemble » seulement, pas sur le gentilé.
population_dans_phrase = population[0].lower() + population[1:]


def ans(valeur: float) -> str:
    """« 0,3 an », « 6,1 ans » : pluriel à partir de 2."""
    return f"{fr_num(valeur)} an" + ("s" if abs(valeur) >= 2 else "")


# ---------------------------------------------------------------------------
# 1. Chiffres clés
# ---------------------------------------------------------------------------

c1, c2, c3, c4 = st.columns(4)
c1.metric("Personnalités", f"{fr_num(bilan['personnalites'])} ans",
          help=f"Âge moyen au décès, {bilan['debut']}–{bilan['fin']}, décès à "
               f"{AGE_ADULTE} ans ou plus")
c2.metric(population, f"{fr_num(bilan['population'])} ans",
          help="Même calcul, sur tous les décès enregistrés en France")
signe = "+" if bilan["ecart"] >= 0 else ""
c3.metric("Écart", f"{signe}{ans(bilan['ecart'])}")
c4.metric("Personnalités comptées", fr_num(bilan["nb_personnalites"], 0))

# ---------------------------------------------------------------------------
# 2. Comparaison par période
# ---------------------------------------------------------------------------

fig = go.Figure()
fig.add_trace(go.Bar(
    x=periodes["libelle"], y=periodes["age_moyen_population"],
    name=population, marker_color="rgba(148, 163, 184, 0.75)",
    hovertemplate="%{x} : %{y:.1f} ans<extra>" + population_dans_phrase + "</extra>",
))
fig.add_trace(go.Bar(
    x=periodes["libelle"], y=periodes["age_moyen_personnalites"],
    name="Personnalités", marker_color=SEX_COLORS[sexe],
    customdata=periodes["nb_personnalites"],
    hovertemplate=("%{x} : %{y:.1f} ans<br>%{customdata} personnalités"
                   "<extra>personnalités</extra>"),
))
fig.update_yaxes(title="Âge moyen au décès (ans)", range=[60, 90])
fig.update_xaxes(title="Période de décès")
apply_layout(fig, height=460, barmode="group",
             legend=dict(orientation="h", yanchor="bottom", y=1.06, x=0),
             title=f"{SEX_LABELS[sexe]} — âge moyen au décès, par période de 5 ans")
st.plotly_chart(fig, width='stretch')

derniere = periodes.iloc[-1]
plus_ou_moins = "plus" if derniere["ecart"] >= 0 else "moins"
note_lecture(
    "<strong>Axe horizontal</strong> : des périodes de 5 ans, "
    f"de {bilan['debut']} à {bilan['fin']}."
    "<br>"
    "<strong>Axe vertical</strong> : l'âge moyen au décès. Il démarre à 60 ans "
    "pour rendre l'écart lisible."
    "<br>"
    f"<strong>Deux barres par période</strong> : en gris, {tous} pendant la "
    "période ; en couleur, les personnalités mortes pendant la même période."
    "<br><br>"
    f"<strong>Exemple, {derniere['libelle']}</strong> : les personnalités "
    f"mortes à cette période avaient en moyenne "
    f"{fr_num(derniere['age_moyen_personnalites'])} ans, contre "
    f"{fr_num(derniere['age_moyen_population'])} ans pour l'{population_dans_phrase}. "
    f"Soit {ans(abs(derniere['ecart']))} de {plus_ou_moins}."
    "<br><br>"
    f"<strong>Seuls les décès à {AGE_ADULTE} ans ou plus sont comptés</strong>, "
    "des deux côtés. On devient rarement célèbre enfant : garder les décès "
    "d'enfants dans la population la ferait paraître mourir plus jeune.",
    f"{repo.millesime('deces_par_age_eurostat')} · "
    f"{repo.millesime('deces_personnalites_wikidata')}",
)

st.warning(
    "**Un écart ne prouve pas que la célébrité fait vivre plus longtemps.**\n\n"
    "- **Vivre longtemps aide à devenir connu.** Une longue carrière laisse plus "
    "d'œuvres, de prix et de postes : plus de chances d'avoir un article "
    "Wikipédia.\n"
    "- **Les personnalités ne sont pas un échantillon de la population.** "
    "Elles sont plus diplômées et plus aisées en moyenne, deux facteurs qui "
    "allongent la vie par eux-mêmes.\n"
    "- **Nationalité française au sens de Wikidata** : les doubles nationaux "
    "sont inclus."
)

download_csv(periodes, f"personnalites_{sexe}")
source_note()
