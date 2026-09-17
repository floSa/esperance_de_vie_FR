import numpy as np
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
from data.repository import AGE_ADULTE, AGE_PREDICTION, DonneesManquantes

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

# ---------------------------------------------------------------------------
# 3. Personnalité par personnalité : avant ou après l'âge prédit ?
# ---------------------------------------------------------------------------

st.markdown("---")
st.subheader("👤 Personnalité par personnalité : avant ou après l'âge prédit ?")
st.caption(
    f"Âge prédit = {AGE_PREDICTION} ans + l'espérance de vie à {AGE_PREDICTION} ans, "
    f"l'année où la personne a eu {AGE_PREDICTION} ans. C'est l'âge auquel elle "
    "pouvait s'attendre à mourir, vu la mortalité de l'époque."
)

debut_commun, fin_commun = repo.annees_communes()
choix_periodes = {f"Toutes ({debut_commun}–{fin_commun})": (debut_commun, fin_commun)}
choix_periodes.update({lib: (a, b) for a, b, lib in repo.periodes_communes()})
persist("periode_prediction", next(iter(choix_periodes)))
col_periode, _ = st.columns([1, 3])
with col_periode:
    periode = st.selectbox("Période de décès", list(choix_periodes), key="periode_prediction")
p_debut, p_fin = choix_periodes[periode]

ecarts, morts_avant_60 = repo.ecarts_personnalites(sexe, p_debut, p_fin)
ecarts_pop = repo.ecarts_population(sexe, p_debut, p_fin)
part_pers, med_pers = repo.part_apres_et_mediane(ecarts["ecart"])
part_pop, med_pop = repo.part_apres_et_mediane(ecarts_pop["ecart"], ecarts_pop["deces"])


feminin = sexe == "femmes"
mort = "morte" if feminin else "mort"
ne = "Née" if feminin else "Né"


def signe_ans(valeur: float) -> str:
    return ("+" if valeur >= 0 else "−") + ans(abs(valeur))


c1, c2, c3, c4 = st.columns(4)
c1.metric("Personnalités mortes après l'âge prédit", f"{part_pers:.0%}".replace("%", " %"))
c2.metric(f"{population} {mort}s après l'âge prédit",
          f"{part_pop:.0%}".replace("%", " %"))
c3.metric("Écart médian, personnalités", signe_ans(med_pers))
c4.metric(f"Écart médian, {population_dans_phrase}", signe_ans(med_pop))
st.caption(
    f"{fr_num(len(ecarts), 0)} personnalités comparées. "
    f"{fr_num(morts_avant_60, 0)} autres sont mortes avant {AGE_PREDICTION} ans : "
    "elles n'ont pas d'âge prédit et ne figurent pas ici."
)

# --- Nuage : toutes les personnalités, un point par naissance × décès --------

VERT, ROUGE = "#16a34a", "#dc2626"

points = repo.points_personnalites(sexe, p_debut, p_fin)
predit = repo.age_predit_par_naissance(sexe)
reference = repo.age_moyen_population_par_naissance(sexe, p_debut, p_fin)
moyenne_pers = repo.age_moyen_personnalites_par_naissance(sexe, p_debut, p_fin)
n_min, n_max = int(points["annee_naissance"].min()), int(points["annee_naissance"].max())
predit = predit[predit["annee_naissance"].between(n_min, n_max)]
reference = reference[reference["annee_naissance"].between(n_min, n_max)]
ZONE = "rgba(100, 116, 139, 0.22)"
AGE_MAX_AXE = max(110, int(points["age"].max()) + 3)

fig_n = go.Figure()
# Zones hors fenêtre d'observation : une génération n'apparaît qu'à travers ses
# décès survenus entre p_debut et p_fin.
naissances = np.arange(n_min - 1, n_max + 2)
fig_n.add_trace(go.Scatter(
    x=np.concatenate([naissances, naissances[::-1]]),
    y=np.concatenate([np.clip(p_debut - naissances, AGE_PREDICTION, AGE_MAX_AXE),
                      np.full(len(naissances), AGE_PREDICTION)]),
    fill="toself", fillcolor=ZONE, line=dict(width=0),
    name="Hors de la période observée", hoverinfo="skip", legendgroup="hors",
))
fig_n.add_trace(go.Scatter(
    x=np.concatenate([naissances, naissances[::-1]]),
    y=np.concatenate([np.clip(p_fin - naissances, AGE_PREDICTION, AGE_MAX_AXE),
                      np.full(len(naissances), AGE_MAX_AXE)]),
    fill="toself", fillcolor=ZONE, line=dict(width=0),
    name="Hors de la période observée", hoverinfo="skip", showlegend=False,
    legendgroup="hors",
))
for nom_trace, masque, couleur in ((f"{mort.capitalize()}s après l'âge prédit", points["ecart"] > 0, VERT),
                                   (f"{mort.capitalize()}s avant l'âge prédit", points["ecart"] <= 0, ROUGE)):
    sous = points[masque]
    fig_n.add_trace(go.Scattergl(
        x=sous["annee_naissance"], y=sous["year"] - sous["annee_naissance"],
        mode="markers", name=nom_trace,
        marker=dict(color=couleur, opacity=0.35,
                    size=np.clip(4 + 2.2 * np.sqrt(sous["nb"]), 5, 22),
                    line=dict(width=0)),
        customdata=np.stack([sous["year"], sous["nb"], sous["ecart"], sous["noms"]], axis=-1),
        hovertemplate=("<b>" + ne + "s en %{x}, " + mort + "s en %{customdata[0]}</b>"
                       "<br>%{customdata[1]} personnalité(s) · écart moyen %{customdata[2]:+.1f} ans"
                       "<br><br>%{customdata[3]}<extra></extra>"),
    ))
fig_n.add_trace(go.Scatter(
    x=reference["annee_naissance"], y=reference["age_moyen"], mode="lines",
    line=dict(color="#334155", width=3), name=f"{population}, même période",
    hovertemplate=(f"{population} " + ne.lower() + "s en %{x}<br>"
                   "âge moyen au décès : %{y:.1f} ans<extra></extra>"),
))
fig_n.add_trace(go.Scatter(
    x=moyenne_pers["annee_naissance"], y=moyenne_pers["age_moyen"], mode="lines",
    line=dict(color=SEX_COLORS[sexe], width=3.5), name="Personnalités, moyenne",
    customdata=moyenne_pers["nb"],
    hovertemplate=("Personnalités " + ne.lower() + "s en %{x}<br>âge moyen au décès : "
                   "%{y:.1f} ans (%{customdata} personnes)<extra></extra>"),
))
fig_n.add_trace(go.Scatter(
    x=predit["annee_naissance"], y=predit["age_predit"], mode="lines",
    line=dict(color="#f97316", width=3, dash="dash"), name="Âge prédit",
    hovertemplate="Âge prédit pour une naissance en %{x} : %{y:.1f} ans<extra></extra>",
))
fig_n.update_xaxes(title="Année de naissance", range=[n_min - 1, n_max + 1])
fig_n.update_yaxes(title="Âge au décès (ans)", range=[AGE_PREDICTION - 1, AGE_MAX_AXE])
apply_layout(fig_n, height=680, margin=dict(b=150),
             legend=dict(orientation="h", yanchor="top", y=-0.14, x=0),
             title=f"{fr_num(len(ecarts), 0)} {SEX_LABELS[sexe].lower()} — {periode}")
st.plotly_chart(fig_n, width='stretch')

ecart_lignes = (moyenne_pers.merge(reference, on="annee_naissance", suffixes=("_pers", "_pop"))
                .assign(ecart=lambda d: d["age_moyen_pers"] - d["age_moyen_pop"]))
note_lecture(
    "<strong>Axe horizontal</strong> : l'année de naissance."
    "<br>"
    "<strong>Axe vertical</strong> : l'âge au décès."
    "<br>"
    "<strong>Chaque point</strong> regroupe les personnalités nées la même année et "
    "mortes la même année. Plus il est gros, plus il en contient. Survolez-le pour "
    "voir les noms et l'écart."
    "<br>"
    f"<strong>Couleur des points</strong> : vert si {mort} après l'âge prédit "
    "(tirets orange), rouge si avant."
    "<br><br>"
    "<strong>Pourquoi vert à gauche et rouge à droite ?</strong> On ne voit que les "
    f"décès entre {p_debut} et {p_fin} : la bande blanche. Les zones grises sont "
    "hors de cette période. Les générations anciennes "
    "n'y figurent que si elles ont vécu très vieux, les récentes que si elles sont "
    "mortes jeunes. Ce n'est pas un effet de la célébrité."
    "<br><br>"
    "<strong>La bonne comparaison : les deux lignes pleines.</strong> La ligne "
    f"colorée est l'âge moyen des personnalités, la ligne foncée celui de l'"
    f"{population_dans_phrase} " + ne.lower() + "s la même année. Toutes deux "
    "subissent le même effet de période. Elles s'arrêtent à 99 ans : au-delà, "
    "Eurostat ne donne pas l'âge exact."
    + (
        f" Ici, la ligne colorée est au-dessus pour {(ecart_lignes['ecart'] > 0).mean():.0%} "
        f"des années de naissance, avec un écart moyen de "
        f"{signe_ans(ecart_lignes['ecart'].mean())}.".replace("%", " %")
        if len(ecart_lignes) else ""
    ),
    repo.millesime("deces_personnalites_wikidata") + " · "
    + repo.millesime("deces_par_age_eurostat") + " · espérance de vie à 60 ans : "
    + repo.millesime("esperance_vie_fr_insee"),
)

# --- Histogramme : toutes les personnalités face à l'ensemble ---------------

LARGEUR = 2
bornes = np.arange(-30, 38 + LARGEUR, LARGEUR)
compte_pers, _ = np.histogram(ecarts["ecart"].clip(bornes[0], bornes[-1] - 1e-9), bins=bornes)
compte_pop, _ = np.histogram(ecarts_pop["ecart"].clip(bornes[0], bornes[-1] - 1e-9),
                             bins=bornes, weights=ecarts_pop["deces"])
pct_pers = 100 * compte_pers / compte_pers.sum()
pct_pop = 100 * compte_pop / compte_pop.sum()
centres = bornes[:-1] + LARGEUR / 2

fig_d = go.Figure()
fig_d.add_trace(go.Bar(
    x=centres, y=pct_pers, width=LARGEUR * 0.92, name="Personnalités",
    marker_color=[VERT if c > 0 else ROUGE for c in centres],
    hovertemplate="Écart %{x:+.0f} ans : %{y:.1f} % des personnalités<extra></extra>",
))
fig_d.add_trace(go.Scatter(
    x=centres, y=pct_pop, mode="lines", line=dict(color="#475569", width=2.5, shape="hvh"),
    name=population,
    hovertemplate="Écart %{x:+.0f} ans : %{y:.1f} % de l'" + population_dans_phrase
                  + "<extra></extra>",
))
fig_d.add_vline(x=0, line_dash="dash", line_color="gray")
fig_d.update_xaxes(title="Écart entre l'âge au décès et l'âge prédit (ans)")
fig_d.update_yaxes(title="Part des décès (%)")
apply_layout(fig_d, height=420, bargap=0,
             legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
             title=(f"Toutes les femmes comparées — {periode}" if feminin
                    else f"Tous les hommes comparés — {periode}"))
st.plotly_chart(fig_d, width='stretch')

note_lecture(
    "<strong>Axe horizontal</strong> : l'écart entre l'âge au décès et l'âge "
    "prédit, en années. À gauche du trait pointillé, mort avant la prédiction ; "
    "à droite, après."
    "<br>"
    "<strong>Axe vertical</strong> : la part des décès qui tombent dans chaque "
    "tranche de 2 ans."
    "<br>"
    "<strong>Les barres</strong> sont les personnalités (rouge avant, vert "
    f"après). <strong>La ligne foncée</strong> est l'{population_dans_phrase}, "
    "calculée de la même façon."
    "<br><br>"
    f"<strong>Plus les barres sont décalées à droite de la ligne, plus les "
    f"personnalités ont dépassé leur prédiction par rapport à l'"
    f"{population_dans_phrase}.</strong> Ici : {part_pers:.0%} des personnalités "
    f"contre {part_pop:.0%} de l'{population_dans_phrase}.".replace("%", " %")
    + "<br><br>"
    f"La ligne dépasse elle aussi souvent zéro : la prédiction repose sur la "
    f"mortalité de l'année des {AGE_PREDICTION} ans, et la mortalité a continué "
    "de baisser ensuite. C'est pour ça qu'il faut comparer les barres à la ligne, "
    "et non à zéro.",
    repo.millesime("deces_par_age_eurostat"),
)

download_csv(
    ecarts[["year", "nom", "annee_naissance", "age", "age_predit", "ecart",
            "nb_editions_wikipedia", "wikidata_id"]],
    f"personnalites_prediction_{sexe}",
)
source_note()
