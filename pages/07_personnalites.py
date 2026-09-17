import numpy as np
import plotly.graph_objects as go
import streamlit as st

from common import (
    SEX_COLORS,
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
from data.repository import AGE_ADULTE, AGE_PREDICTION, TOUS, DonneesManquantes

st.set_page_config(page_title="Personnalités · Espérance de vie", page_icon="🎭", layout="wide")
render_sidebar()

st.title("🎭 Âge au décès des personnalités françaises")
st.caption(
    "Comparaison avec l'ensemble des Français décédés sur la même période. "
    "Sources : Wikidata, Eurostat, INSEE."
)

# Clé propre à la page : les autres pages ne proposent pas « tous ».
persist("sexe_personnalites", TOUS)
LIBELLES = {TOUS: "Femmes et hommes", "femmes": "Femmes", "hommes": "Hommes"}
col_sexe, _ = st.columns([1, 3])
with col_sexe:
    sexe = st.selectbox(
        "Sexe", [TOUS, "femmes", "hommes"],
        format_func=lambda s: {TOUS: "Tous", "femmes": "Femmes", "hommes": "Hommes"}[s],
        key="sexe_personnalites",
    )

try:
    periodes = repo.comparaison_age_deces(sexe)
    bilan = repo.bilan_age_deces(sexe)
except DonneesManquantes as e:
    st.error(
        f"Données manquantes : {e}\n\nLa liste des personnalités provient du projet "
        "`deces_personnalites_FR`. Lancer sa collecte, puis "
        "`uv run python -m scripts.refresh_data` dans ce projet."
    )
    st.stop()

feminin = sexe == "femmes"
population = "Ensemble des Françaises" if feminin else "Ensemble des Français"
population_dans_phrase = population[0].lower() + population[1:]
morts = "mortes" if feminin else "morts"
nes = "nées" if feminin else "nés"
libelle = LIBELLES[sexe]
couleur = SEX_COLORS.get(sexe, "#7c3aed")
zone = SEX_ZONES.get(sexe, "rgba(124, 58, 237, 0.2)")
VERT, ROUGE, GRIS_POINT = "#16a34a", "#dc2626", "#94a3b8"


def ans(valeur: float) -> str:
    """« 0,3 an », « 6,1 ans » : pluriel à partir de 2."""
    return f"{fr_num(valeur)} an" + ("s" if abs(valeur) >= 2 else "")


def signe_ans(valeur: float) -> str:
    return ("+" if valeur >= 0 else "−") + ans(abs(valeur))


def pct(valeur: float) -> str:
    return f"{valeur:.0%}".replace("%", " %")


def sources(*noms: str) -> str:
    return " · ".join(repo.millesime(n) for n in noms)


# ---------------------------------------------------------------------------
# 1. Âge moyen au décès par période
# ---------------------------------------------------------------------------

st.subheader("Âge moyen au décès par période de 5 ans")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Personnalités", f"{fr_num(bilan['personnalites'])} ans",
          help=f"Âge moyen au décès, {bilan['debut']}–{bilan['fin']}, décès à "
               f"{AGE_ADULTE} ans ou plus")
c2.metric(population, f"{fr_num(bilan['population'])} ans",
          help="Même calcul sur l'ensemble des décès enregistrés en France")
c3.metric("Écart", signe_ans(bilan["ecart"]))
c4.metric("Personnalités comptées", fr_num(bilan["nb_personnalites"], 0))

fig = go.Figure()
fig.add_trace(go.Bar(
    x=periodes["libelle"], y=periodes["age_moyen_population"],
    name=population, marker_color="rgba(148, 163, 184, 0.75)",
    hovertemplate="%{x} : %{y:.1f} ans<extra>" + population_dans_phrase + "</extra>",
))
fig.add_trace(go.Bar(
    x=periodes["libelle"], y=periodes["age_moyen_personnalites"],
    name="Personnalités", marker_color=couleur,
    customdata=periodes["nb_personnalites"],
    hovertemplate="%{x} : %{y:.1f} ans<br>%{customdata} personnalités<extra></extra>",
))
fig.update_yaxes(title="Âge moyen au décès (ans)", range=[60, 90])
fig.update_xaxes(title="Période de décès")
apply_layout(fig, height=460, barmode="group",
             legend=dict(orientation="h", yanchor="bottom", y=1.06, x=0),
             title=f"{libelle} — âge moyen au décès")
st.plotly_chart(fig, width='stretch')

derniere = periodes.iloc[-1]
note_lecture(
    "<strong>Axe horizontal</strong> : périodes de décès de 5 ans, "
    f"{bilan['debut']}–{bilan['fin']}."
    "<br>"
    "<strong>Axe vertical</strong> : âge moyen au décès, à partir de 60 ans."
    "<br>"
    f"<strong>Barres</strong> : en gris, l'{population_dans_phrase} {morts} sur la "
    "période ; en couleur, les personnalités mortes sur la même période."
    "<br><br>"
    f"<strong>{derniere['libelle']}</strong> : "
    f"{fr_num(derniere['age_moyen_personnalites'])} ans pour les personnalités, "
    f"{fr_num(derniere['age_moyen_population'])} ans pour l'{population_dans_phrase}, "
    f"soit un écart de {signe_ans(derniere['ecart'])}."
    "<br>"
    f"Seuls les décès à {AGE_ADULTE} ans ou plus sont comptés, des deux côtés.",
    sources("deces_par_age_eurostat", "deces_personnalites_wikidata"),
)

st.info(
    "**Limites de l'interprétation**\n\n"
    "- Un écart ne mesure pas un effet de la célébrité : une vie longue laisse "
    "davantage de temps pour devenir connu.\n"
    "- Les personnalités sont en moyenne plus diplômées et plus aisées que "
    "l'ensemble de la population, deux facteurs associés à une vie plus longue.\n"
    "- Nationalité française au sens de Wikidata, doubles nationaux inclus."
)
download_csv(periodes, f"personnalites_periodes_{sexe}")

# ---------------------------------------------------------------------------
# 2. Écart à l'âge prédit
# ---------------------------------------------------------------------------

st.markdown("---")
st.subheader("Écart à l'âge prédit")
st.caption(
    f"Âge prédit : {AGE_PREDICTION} ans + espérance de vie à {AGE_PREDICTION} ans, "
    f"l'année des {AGE_PREDICTION} ans, pour le sexe de la personne (INSEE). "
    "Écart : âge au décès moins âge prédit."
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

c1, c2, c3, c4 = st.columns(4)
c1.metric("Personnalités décédées après l'âge prédit", pct(part_pers))
c2.metric(f"{population} {morts} après l'âge prédit", pct(part_pop))
c3.metric("Écart médian, personnalités", signe_ans(med_pers))
c4.metric(f"Écart médian, {population_dans_phrase}", signe_ans(med_pop))
st.caption(
    f"{fr_num(len(ecarts), 0)} personnalités comparées. "
    f"{fr_num(morts_avant_60, 0)} personnalités décédées avant {AGE_PREDICTION} ans "
    "n'ont pas d'âge prédit."
)

# --- 2.1 Nuage par année de décès -------------------------------------------

st.markdown(f"#### Âge au décès par année de décès — {periode}")

points = repo.points_personnalites(sexe, p_debut, p_fin)
lignes_annee = repo.age_moyen_par_annee_deces(sexe, p_debut, p_fin)

fig_n = go.Figure()
for nom_trace, masque, teinte in (
    ("Décès après l'âge prédit", points["ecart"] > 0, VERT),
    ("Décès avant l'âge prédit", points["ecart"] <= 0, ROUGE),
    (f"Décès avant {AGE_PREDICTION} ans, sans âge prédit", points["ecart"].isna(), GRIS_POINT),
):
    sous = points[masque]
    fig_n.add_trace(go.Scattergl(
        x=sous["year"], y=sous["age"], mode="markers", name=nom_trace,
        marker=dict(color=teinte, opacity=0.4,
                    size=np.clip(4 + 2.2 * np.sqrt(sous["nb"]), 5, 22), line=dict(width=0)),
        customdata=np.stack([sous["annee_naissance"], sous["nb"], sous["noms"]], axis=-1),
        hovertemplate=("<b>Décès en %{x}, naissance en %{customdata[0]}</b>"
                       "<br>%{customdata[1]} personnalité(s)<br><br>%{customdata[2]}"
                       "<extra></extra>"),
    ))
fig_n.add_trace(go.Scatter(
    x=lignes_annee["year"], y=lignes_annee["age_moyen_population"], mode="lines",
    line=dict(color="#334155", width=3), name=f"{population}, âge moyen au décès",
    hovertemplate=f"{population}, %{{x}} : %{{y:.1f}} ans<extra></extra>",
))
fig_n.add_trace(go.Scatter(
    x=lignes_annee["year"], y=lignes_annee["age_moyen_personnalites"], mode="lines",
    line=dict(color=couleur, width=3.5), name="Personnalités, âge moyen au décès",
    customdata=lignes_annee["nb_personnalites"],
    hovertemplate="Personnalités, %{x} : %{y:.1f} ans (%{customdata} décès)<extra></extra>",
))
fig_n.update_xaxes(title="Année de décès", range=[p_debut - 0.7, p_fin + 0.7])
fig_n.update_yaxes(title="Âge au décès (ans)",
                   range=[AGE_ADULTE - 2, max(110, int(points["age"].max()) + 3)])
apply_layout(fig_n, height=680, margin=dict(b=150),
             legend=dict(orientation="h", yanchor="top", y=-0.14, x=0),
             title=f"{libelle} — {fr_num(int(points['nb'].sum()), 0)} personnalités")
st.plotly_chart(fig_n, width='stretch')

derniere_annee = lignes_annee.iloc[-1]
deces_periode = repo.deces_population()
deces_periode = deces_periode[
    (deces_periode["sexe"].isin(["femmes", "hommes"] if sexe == TOUS else [sexe]))
    & deces_periode["year"].between(p_debut, p_fin) & (deces_periode["age"] >= AGE_ADULTE)]
part_precoce_pop = float(deces_periode.loc[deces_periode["age"] < AGE_PREDICTION, "deces"].sum()
                         / deces_periode["deces"].sum())
part_precoce_pers = float(points.loc[points["ecart"].isna(), "nb"].sum() / points["nb"].sum())

note_lecture(
    "<strong>Axe horizontal</strong> : année de décès."
    "<br>"
    "<strong>Axe vertical</strong> : âge au décès."
    "<br>"
    "<strong>Points</strong> : personnalités décédées la même année et nées la même "
    "année. La taille croît avec leur nombre. Survoler un point pour afficher les noms."
    "<br>"
    f"<strong>Couleurs</strong> : vert, décès après l'âge prédit ; rouge, avant ; gris, "
    f"décès avant {AGE_PREDICTION} ans."
    "<br>"
    "<strong>Lignes</strong> : âge moyen au décès des personnalités (couleur) et de "
    f"l'{population_dans_phrase} (foncé), par année, décès à {AGE_ADULTE} ans ou plus."
    "<br><br>"
    f"<strong>{int(derniere_annee['year'])}</strong> : "
    f"{fr_num(derniere_annee['age_moyen_personnalites'])} ans pour les personnalités, "
    f"{fr_num(derniere_annee['age_moyen_population'])} ans pour l'{population_dans_phrase}."
    "<br>"
    "Les lignes comparent des personnes décédées la même année, et non nées la même "
    f"année. Part des décès avant {AGE_PREDICTION} ans : {pct(part_precoce_pop)} dans "
    f"l'{population_dans_phrase}, {pct(part_precoce_pers)} chez les personnalités.",
    sources("deces_personnalites_wikidata", "deces_par_age_eurostat", "esperance_vie_fr_insee"),
)

# --- 2.2 Boîtes à moustaches par année de décès -----------------------------

st.markdown(f"#### Distribution annuelle de l'âge au décès des personnalités — {periode}")

boites_pop = repo.boites_population_par_annee_deces(sexe, p_debut, p_fin)
pers_annee = repo.personnalites_par_annee_deces(sexe, p_debut, p_fin)

fig_b = go.Figure()
fig_b.add_trace(go.Box(
    x=pers_annee["year"], y=pers_annee["age"], name="Personnalités",
    marker=dict(color=couleur, size=4, opacity=0.6),
    fillcolor=zone, line=dict(color=couleur, width=1.5),
    boxpoints="outliers", boxmean=True,
    hovertext=pers_annee["nom"] + " — " + pers_annee["age"].astype(str) + " ans",
    hoverinfo="text+y",
))
fig_b.add_trace(go.Scatter(
    x=boites_pop["year"], y=boites_pop["mediane"], mode="lines+markers",
    line=dict(color="#334155", width=2.5), marker=dict(size=5),
    name=f"{population}, âge médian au décès",
    hovertemplate=f"{population}, %{{x}} : âge médian %{{y:.0f}} ans<extra></extra>",
))
fig_b.update_xaxes(title="Année de décès", dtick=5)
fig_b.update_yaxes(title="Âge au décès (ans)")
apply_layout(fig_b, height=560, margin=dict(b=120),
             legend=dict(orientation="h", yanchor="top", y=-0.14, x=0),
             title=f"{libelle} — une boîte par année")
st.plotly_chart(fig_b, width='stretch')

derniere_boite = boites_pop.iloc[-1]
ages_derniere = pers_annee.loc[pers_annee["year"] == derniere_boite["year"], "age"]
note_lecture(
    "<strong>Axe horizontal</strong> : année de décès."
    "<br>"
    "<strong>Axe vertical</strong> : âge au décès."
    "<br>"
    "<strong>Boîte</strong> : moitié centrale des âges au décès des personnalités. "
    "Trait plein : âge médian. Trait pointillé : âge moyen. Moustaches : âges extrêmes "
    "usuels. Points isolés : personnalités décédées à un âge inhabituel pour l'année ; "
    "survoler pour afficher le nom."
    "<br>"
    f"<strong>Ligne foncée</strong> : âge médian au décès de l'{population_dans_phrase}, "
    f"décès à {AGE_ADULTE} ans ou plus."
    "<br><br>"
    f"<strong>{int(derniere_boite['year'])}</strong> : âge médian de "
    f"{int(ages_derniere.median())} ans pour les personnalités, moitié centrale entre "
    f"{int(ages_derniere.quantile(0.25))} et {int(ages_derniere.quantile(0.75))} ans ; "
    f"âge médian de {int(derniere_boite['mediane'])} ans pour l'{population_dans_phrase}.",
    sources("deces_personnalites_wikidata", "deces_par_age_eurostat"),
)

# --- 2.3 Écart moyen à l'âge prédit (barycentre) ----------------------------

st.markdown("#### Écart moyen à l'âge prédit par période de 5 ans")

barycentres = repo.ecart_moyen_par_periode(sexe)

fig_g = go.Figure()
fig_g.add_hline(y=0, line_dash="dash", line_color="gray",
                annotation_text="Décès à l'âge prédit", annotation_position="top left")
fig_g.add_trace(go.Scatter(
    x=barycentres["libelle"], y=barycentres["ecart_moyen_population"],
    mode="lines+markers", line=dict(color="#334155", width=2.5), marker=dict(size=8),
    name=population,
    hovertemplate="%{x} : écart moyen %{y:+.1f} ans<extra>" + population_dans_phrase
                  + "</extra>",
))
fig_g.add_trace(go.Scatter(
    x=barycentres["libelle"], y=barycentres["ecart_moyen_personnalites"],
    mode="lines+markers", line=dict(color=couleur, width=3), marker=dict(size=10),
    error_y=dict(type="data", array=barycentres["marge_ic95"], thickness=1.5, width=6),
    name="Personnalités (intervalle de confiance à 95 %)",
    customdata=barycentres["nb_personnalites"],
    hovertemplate=("%{x} : écart moyen %{y:+.1f} ans<br>%{customdata} personnalités"
                   "<extra></extra>"),
))
fig_g.update_xaxes(title="Période de décès")
fig_g.update_yaxes(title="Écart moyen à l'âge prédit (ans)", zeroline=False)
apply_layout(fig_g, height=460, margin=dict(b=110),
             legend=dict(orientation="h", yanchor="top", y=-0.2, x=0),
             title=f"{libelle} — écart moyen à l'âge prédit")
st.plotly_chart(fig_g, width='stretch')

dernier_g = barycentres.iloc[-1]
note_lecture(
    "<strong>Axe horizontal</strong> : périodes de décès de 5 ans."
    "<br>"
    "<strong>Axe vertical</strong> : écart moyen entre l'âge au décès et l'âge prédit. "
    "Au-dessus de zéro, décès en moyenne après l'âge prédit ; en dessous, avant."
    "<br>"
    "<strong>Points</strong> : barycentre des écarts de chaque groupe. Barres "
    "verticales : intervalle de confiance à 95 % de la moyenne des personnalités."
    "<br><br>"
    f"<strong>{dernier_g['libelle']}</strong> : écart moyen de "
    f"{signe_ans(dernier_g['ecart_moyen_personnalites'])} pour les personnalités, "
    f"{signe_ans(dernier_g['ecart_moyen_population'])} pour l'{population_dans_phrase}."
    "<br>"
    f"Décès à {AGE_PREDICTION} ans ou plus uniquement. L'âge prédit repose sur la "
    f"mortalité de l'année des {AGE_PREDICTION} ans, qui a baissé ensuite : comparer les "
    "deux lignes entre elles, et non chacune à zéro.",
    sources("deces_personnalites_wikidata", "deces_par_age_eurostat", "esperance_vie_fr_insee"),
)
download_csv(barycentres, f"personnalites_ecart_moyen_{sexe}")

# --- 2.4 Nuage par année de naissance ---------------------------------------

st.markdown(f"#### Âge au décès par année de naissance — {periode}")

points_n = points[points["ecart"].notna()].assign(
    age_atteint=lambda d: d["year"] - d["annee_naissance"])
predit = repo.age_predit_par_naissance(sexe)
reference = repo.age_moyen_population_par_naissance(sexe, p_debut, p_fin)
moyenne_pers = repo.age_moyen_personnalites_par_naissance(sexe, p_debut, p_fin)
n_min, n_max = int(points_n["annee_naissance"].min()), int(points_n["annee_naissance"].max())
predit = predit[predit["annee_naissance"].between(n_min, n_max)]
reference = reference[reference["annee_naissance"].between(n_min, n_max)]
age_max_axe = max(110, int(points_n["age_atteint"].max()) + 3)
ZONE_HORS = "rgba(100, 116, 139, 0.22)"

fig_nais = go.Figure()
naissances = np.arange(n_min - 1, n_max + 2)
for bordure, remplissage, legende in (
    (np.clip(p_debut - naissances, AGE_PREDICTION, age_max_axe), AGE_PREDICTION, True),
    (np.clip(p_fin - naissances, AGE_PREDICTION, age_max_axe), age_max_axe, False),
):
    fig_nais.add_trace(go.Scatter(
        x=np.concatenate([naissances, naissances[::-1]]),
        y=np.concatenate([bordure, np.full(len(naissances), remplissage)]),
        fill="toself", fillcolor=ZONE_HORS, line=dict(width=0), hoverinfo="skip",
        name="Hors de la période observée", legendgroup="hors", showlegend=legende,
    ))
for nom_trace, masque, teinte in (("Décès après l'âge prédit", points_n["ecart"] > 0, VERT),
                                  ("Décès avant l'âge prédit", points_n["ecart"] <= 0, ROUGE)):
    sous = points_n[masque]
    fig_nais.add_trace(go.Scattergl(
        x=sous["annee_naissance"], y=sous["age_atteint"], mode="markers", name=nom_trace,
        marker=dict(color=teinte, opacity=0.35,
                    size=np.clip(4 + 2.2 * np.sqrt(sous["nb"]), 5, 22), line=dict(width=0)),
        customdata=np.stack([sous["year"], sous["nb"], sous["ecart"], sous["noms"]], axis=-1),
        hovertemplate=("<b>Naissance en %{x}, décès en %{customdata[0]}</b>"
                       "<br>%{customdata[1]} personnalité(s) · écart moyen "
                       "%{customdata[2]:+.1f} ans<br><br>%{customdata[3]}<extra></extra>"),
    ))
fig_nais.add_trace(go.Scatter(
    x=reference["annee_naissance"], y=reference["age_moyen"], mode="lines",
    line=dict(color="#334155", width=3), name=f"{population}, âge moyen au décès",
    hovertemplate=f"{population}, naissance en %{{x}} : %{{y:.1f}} ans<extra></extra>",
))
fig_nais.add_trace(go.Scatter(
    x=moyenne_pers["annee_naissance"], y=moyenne_pers["age_moyen"], mode="lines",
    line=dict(color=couleur, width=3.5), name="Personnalités, âge moyen au décès",
    customdata=moyenne_pers["nb"],
    hovertemplate=("Personnalités, naissance en %{x} : %{y:.1f} ans "
                   "(%{customdata} personnes)<extra></extra>"),
))
for sexe_predit, tirets in (("femmes", "dash"), ("hommes", "dot")):
    courbe = predit[predit["sexe"] == sexe_predit]
    if courbe.empty:
        continue
    fig_nais.add_trace(go.Scatter(
        x=courbe["annee_naissance"], y=courbe["age_predit"], mode="lines",
        line=dict(color="#f97316", width=2.5, dash=tirets),
        name="Âge prédit" if sexe != TOUS else f"Âge prédit, {sexe_predit}",
        hovertemplate="Âge prédit, naissance en %{x} : %{y:.1f} ans<extra></extra>",
    ))
fig_nais.update_xaxes(title="Année de naissance", range=[n_min - 1, n_max + 1])
fig_nais.update_yaxes(title="Âge au décès (ans)", range=[AGE_PREDICTION - 1, age_max_axe])
apply_layout(fig_nais, height=680, margin=dict(b=150),
             legend=dict(orientation="h", yanchor="top", y=-0.14, x=0),
             title=f"{libelle} — décès à {AGE_PREDICTION} ans ou plus")
st.plotly_chart(fig_nais, width='stretch')

ecart_lignes = (moyenne_pers.merge(reference, on="annee_naissance", suffixes=("_pers", "_pop"))
                            .assign(ecart=lambda d: d["age_moyen_pers"] - d["age_moyen_pop"]))
note_lecture(
    "<strong>Axe horizontal</strong> : année de naissance."
    "<br>"
    "<strong>Axe vertical</strong> : âge au décès."
    "<br>"
    "<strong>Points</strong> : personnalités nées la même année et décédées la même "
    "année ; vert après l'âge prédit (tirets orange), rouge avant. Survoler un point "
    "pour afficher les noms."
    "<br>"
    f"<strong>Zones grises</strong> : âges non observables, les décès étant limités à "
    f"{p_debut}–{p_fin}. Les générations anciennes n'apparaissent qu'à des âges élevés, "
    "les générations récentes qu'à des âges faibles : la répartition des couleurs en "
    "découle."
    "<br>"
    "<strong>Lignes pleines</strong> : âge moyen au décès des personnalités (couleur) et "
    f"de l'{population_dans_phrase} (foncé) nés la même année, soumis à la même période "
    "d'observation. Décès de 60 à 99 ans, Eurostat ne détaillant pas les âges au-delà."
    + (
        f"<br><br>Ligne des personnalités au-dessus de celle de l'{population_dans_phrase} "
        f"pour {pct((ecart_lignes['ecart'] > 0).mean())} des années de naissance ; écart "
        f"moyen de {signe_ans(ecart_lignes['ecart'].mean())}."
        if len(ecart_lignes) else ""
    ),
    sources("deces_personnalites_wikidata", "deces_par_age_eurostat", "esperance_vie_fr_insee"),
)

# --- 2.5 Répartition des écarts ---------------------------------------------

st.markdown(f"#### Répartition des écarts à l'âge prédit — {periode}")

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
    hovertemplate=("Écart %{x:+.0f} ans : %{y:.1f} % de l'" + population_dans_phrase
                   + "<extra></extra>"),
))
fig_d.add_vline(x=0, line_dash="dash", line_color="gray")
fig_d.update_xaxes(title="Écart entre l'âge au décès et l'âge prédit (ans)")
fig_d.update_yaxes(title="Part des décès (%)")
apply_layout(fig_d, height=420, bargap=0,
             legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
             title=f"{libelle} — part des décès par tranche d'écart de 2 ans")
st.plotly_chart(fig_d, width='stretch')

note_lecture(
    "<strong>Axe horizontal</strong> : écart entre l'âge au décès et l'âge prédit. "
    "À gauche du trait pointillé, décès avant l'âge prédit ; à droite, après."
    "<br>"
    "<strong>Axe vertical</strong> : part des décès dans chaque tranche de 2 ans."
    "<br>"
    "<strong>Barres</strong> : personnalités (rouge avant, vert après). "
    f"<strong>Ligne</strong> : {population_dans_phrase}, même calcul."
    "<br><br>"
    f"Décès après l'âge prédit : {pct(part_pers)} des personnalités, "
    f"{pct(part_pop)} de l'{population_dans_phrase}. Comparer les barres à la ligne, "
    "et non au zéro.",
    sources("deces_par_age_eurostat"),
)

download_csv(
    ecarts[["year", "sexe", "nom", "annee_naissance", "age", "age_predit", "ecart",
            "nb_editions_wikipedia", "wikidata_id"]],
    f"personnalites_prediction_{sexe}",
)
source_note()
