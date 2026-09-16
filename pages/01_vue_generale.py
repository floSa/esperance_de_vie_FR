import plotly.express as px
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
    persist,
    render_sidebar,
    source_note,
)
from data import repository as repo

st.set_page_config(page_title="Vue générale · Espérance de vie", page_icon="📈", layout="wide")
render_sidebar()

longue = repo.esperance_vie_longue()

st.title("📈 Vue générale — France")

# ---------------------------------------------------------------------------
# 1. Sélection de l'âge
# ---------------------------------------------------------------------------

ages = repo.ages_disponibles()
persist("age_observe", 0)
age = st.select_slider(
    "Espérance de vie à l'âge de…",
    options=ages,
    format_func=lambda a: "la naissance" if a == 0 else f"{a} ans",
    key="age_observe",
)
libelle_age = "la naissance" if age == 0 else f"{age} ans"
serie = repo.serie_par_sexe(age)
y_label = ("Espérance de vie à la naissance (ans)" if age == 0
           else f"Années restant à vivre à {age} ans")

# ---------------------------------------------------------------------------
# 2. Métriques de l'âge sélectionné
# ---------------------------------------------------------------------------

derniere = serie.iloc[-1]
premiere = serie.iloc[0]
an_recent, an_ancien = int(derniere["year"]), int(premiere["year"])
gain_f = float(derniere["femmes"] - premiere["femmes"])

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric(
    "Âge observé",
    "Naissance" if age == 0 else f"{age} ans",
    help="Âge sélectionné avec le curseur ci-dessus",
)
c2.metric(
    f"Femmes, {an_recent}",
    f"{fr_num(derniere['femmes'])} ans",
    help=f"Années restant à vivre à {libelle_age}",
)
c3.metric(f"Hommes, {an_recent}", f"{fr_num(derniere['hommes'])} ans")
c4.metric("Écart femmes − hommes",
          f"{fr_num(derniere['femmes'] - derniere['hommes'])} ans")
c5.metric(
    f"Gain femmes depuis {an_ancien}",
    f"+{fr_num(gain_f)} ans",
    help=f"Première année disponible pour cet âge : {an_ancien}",
)

if age != 0:
    st.caption(
        f"Une femme ayant atteint {age} ans en {an_recent} peut espérer vivre "
        f"encore **{fr_num(derniere['femmes'])} ans**, soit un décès vers "
        f"**{fr_num(age + derniere['femmes'], 0)} ans**."
    )

# ---------------------------------------------------------------------------
# 3. Évolution
# ---------------------------------------------------------------------------

annee_max = an_recent

fig = go.Figure()

# Pour l'espérance à la naissance, la série longue tous sexes confondus fait
# apparaître 1918 et 1940, que les séries par sexe (à partir de 1946) ratent.
if age == 0:
    fig.add_trace(go.Scatter(
        x=longue["year"], y=longue["esperance"],
        line=dict(color="rgba(140,140,140,0.75)", width=1.5),
        name="Tous sexes (série longue)",
        hovertemplate="%{x} : %{y:.1f} ans<extra>tous sexes</extra>",
    ))

for sexe, couleur in (("femmes", COLOR_FEMMES), ("hommes", COLOR_HOMMES)):
    fig.add_trace(go.Scatter(
        x=serie["year"], y=serie[sexe],
        line=dict(color=couleur, width=2.5),
        name=sexe.capitalize(),
        hovertemplate="%{x} : %{y:.1f} ans<extra>" + sexe + "</extra>",
    ))

if age == 0:
    for x, txt in ((1918, "1918"), (1940, "1940"), (2020, "Covid")):
        fig.add_vline(x=x, line_dash="dot", line_color="gray", opacity=0.5)
        fig.add_annotation(x=x, y=1.04, yref="paper", text=txt, showarrow=False,
                           font=dict(size=11))
    fig.update_xaxes(range=[1900, annee_max])

fig.update_yaxes(title=y_label)
fig.update_xaxes(title="Année")
apply_layout(fig, height=480, legend=dict(orientation="h", yanchor="bottom", y=1.08, x=0))
st.plotly_chart(fig, width='stretch')

if age == 0:
    note_lecture(
        "L'axe vertical est le nombre d'années qu'un nouveau-né vivrait si les "
        "conditions de mortalité de son année de naissance restaient figées toute "
        "sa vie. Ce n'est donc <em>pas</em> une prédiction, mais un résumé de la "
        "mortalité de l'année. C'est ce qui explique les chutes brutales : en "
        "<strong>1918</strong>, la grippe espagnole et la guerre font tomber "
        "l'indicateur à <strong>34,8 ans</strong> contre 43,0 l'année précédente — "
        "puis il remonte aussitôt. La courbe grise couvre les deux sexes depuis "
        "1816 ; les courbes rose et bleue commencent en 1946, première année où "
        "l'INSEE publie le détail par sexe.",
        f"{repo.millesime('esperance_vie_fr_longue_owid')} · "
        f"{repo.millesime('esperance_vie_fr_insee')}",
    )
else:
    exemple = round(float(derniere["femmes"]))
    note_lecture(
        f"L'axe vertical est le nombre d'années qu'il reste à vivre, en moyenne, "
        f"à une personne <strong>déjà âgée de {age} ans</strong>. Ce n'est donc "
        f"pas un âge mais une durée : lire un point à {exemple} signifie "
        f"« encore {exemple} ans à vivre », soit un décès vers "
        f"{age + exemple} ans."
        "<br><br>"
        f"Cette durée ne concerne que les personnes ayant atteint {age} ans. "
        "Celles décédées avant n'entrent pas dans le calcul — c'est pourquoi "
        f"{age} + cette durée dépasse l'espérance de vie à la naissance."
        "<br><br>"
        + (
            f"La série commence en {an_ancien} : l'INSEE publie cet âge depuis "
            "1946."
            if age in repo.AGES_INSEE else
            f"La série commence en {an_ancien}. L'INSEE ne publie que les âges "
            "0, 1, 20, 40 et 60 ans, qui remontent à 1946 ; tous les autres âges "
            "viennent d'Eurostat, dont la série française démarre en 1998."
        ),
        repo.millesime(repo.source_de_l_age(age)),
    )

# ---------------------------------------------------------------------------
# 3. Comparaison européenne
# ---------------------------------------------------------------------------

annee_eu = repo.annee_europe()
st.subheader(f"🇪🇺 Comparaison européenne ({annee_eu})")

pays = repo.europe()
moyenne = repo.moyenne_ue()

fig_eu = px.bar(
    pays, x="e0_total", y="country", orientation="h",
    color="e0_total", color_continuous_scale="Blues",
    labels={"e0_total": "Espérance de vie à la naissance (ans)", "country": ""},
)
fig_eu.update_traces(
    marker_line_color=COLOR_E0,
    marker_line_width=[2.5 if c == "FR" else 0 for c in pays["code"]],
    hovertemplate="%{y} : %{x:.1f} ans<extra></extra>",
)
fig_eu.update_yaxes(categoryorder="total ascending")
fig_eu.update_xaxes(range=[70, 86])
if moyenne is not None:
    fig_eu.add_vline(
        x=moyenne, line_dash="dash", line_color=COLOR_E0,
        annotation_text=f"Moyenne UE-27 : {fr_num(moyenne)} ans",
        annotation_position="top left",
    )
apply_layout(fig_eu, height=680, coloraxis_showscale=False)
st.plotly_chart(fig_eu, width='stretch')

rang_fr = int(pays.index[pays["code"] == "FR"][0]) + 1
note_lecture(
    f"Un pays par barre, classé du plus élevé au plus bas, tous sexes confondus. "
    f"La <strong>France est cerclée d'orange</strong> et arrive "
    f"<strong>{rang_fr}<sup>e</sup> sur {len(pays)}</strong>, au-dessus de la "
    f"moyenne UE-27 (trait orange pointillé). L'échelle démarre à 70 ans pour "
    "rendre les écarts lisibles : visuellement les barres semblent très "
    "inégales, mais l'ensemble des 27 tient en un peu plus de 8 ans.",
    repo.millesime("esperance_vie_europe_eurostat"),
)

# ---------------------------------------------------------------------------
# 4. Tableaux récapitulatifs
# ---------------------------------------------------------------------------

fmt = {
    "e0_f": st.column_config.NumberColumn("e₀ femmes", format="%.1f"),
    "e0_m": st.column_config.NumberColumn("e₀ hommes", format="%.1f"),
    "e0_total": st.column_config.NumberColumn("e₀ total", format="%.1f"),
    "ecart_fh": st.column_config.NumberColumn("Écart F−H", format="%.1f"),
    "country": st.column_config.TextColumn("Pays"),
}
col_g, col_d = st.columns(2)
with col_g:
    st.markdown("**Top 10 — e₀ femmes le plus élevé**")
    st.dataframe(pays.nlargest(10, "e0_f")[["country", "e0_f", "e0_m", "e0_total"]],
                 column_config=fmt, hide_index=True, width='stretch')
with col_d:
    st.markdown("**Top 10 — écart femmes/hommes le plus important**")
    st.dataframe(pays.nlargest(10, "ecart_fh")[["country", "ecart_fh", "e0_f", "e0_m"]],
                 column_config=fmt, hide_index=True, width='stretch')
st.caption(
    "L'écart femmes−hommes est le plus fort dans les pays baltes et le plus "
    "faible aux Pays-Bas et en Suède : il reflète surtout la surmortalité "
    "masculine aux âges actifs."
)

download_csv(serie, "vue_generale")
source_note()
