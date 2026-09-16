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
    render_sidebar,
    source_note,
)
from data import repository as repo

st.set_page_config(page_title="Vue générale · Espérance de vie", page_icon="📈", layout="wide")
render_sidebar()

serie_e0 = repo.serie_par_sexe(0)
annee_max = int(serie_e0["year"].max())
derniere = serie_e0.iloc[-1]

st.title(f"📈 Vue générale — France 1900–{annee_max}")

# ---------------------------------------------------------------------------
# 1. Métriques
# ---------------------------------------------------------------------------

longue = repo.esperance_vie_longue()
e0_1900 = float(longue.loc[longue["year"] == 1900, "esperance"].iloc[0])

c1, c2, c3, c4 = st.columns(4)
c1.metric(f"e₀ femmes {annee_max}", f"{fr_num(derniere['femmes'])} ans")
c2.metric(f"e₀ hommes {annee_max}", f"{fr_num(derniere['hommes'])} ans")
c3.metric("Écart F/H", f"{fr_num(derniere['femmes'] - derniere['hommes'])} ans")
c4.metric(
    "Gain depuis 1900",
    f"+{fr_num((derniere['femmes'] + derniere['hommes']) / 2 - e0_1900)} ans",
    help="Écart entre la moyenne des deux sexes aujourd'hui et l'espérance "
         "tous sexes confondus de 1900",
)

# ---------------------------------------------------------------------------
# 2. Évolution
# ---------------------------------------------------------------------------

INDICATEURS = {
    "À la naissance": (0, "Espérance de vie à la naissance (ans)"),
    "À 1 an": (1, "Années restant à vivre à 1 an"),
    "À 20 ans": (20, "Années restant à vivre à 20 ans"),
    "À 40 ans": (40, "Années restant à vivre à 40 ans"),
    "À 60 ans": (60, "Années restant à vivre à 60 ans"),
    "À 65 ans": (65, "Années restant à vivre à 65 ans"),
}
choix = st.radio(
    "Espérance de vie mesurée…", list(INDICATEURS),
    horizontal=True, key="indicateur_page1",
)
age, y_label = INDICATEURS[choix]
serie = repo.serie_par_sexe(age)

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
    note_lecture(
        f"L'axe vertical est le nombre d'années qu'il reste à vivre, en moyenne, "
        f"à une personne <strong>déjà âgée de {age} ans</strong>. Ce n'est donc "
        "pas un âge, mais une durée : lire un point à 28 signifie « encore 28 ans "
        f"à vivre », soit un décès vers {age + 28} ans."
        "<br><br>Cette durée ne concerne que les personnes ayant atteint "
        f"{age} ans. Celles décédées avant n'entrent pas dans le calcul — c'est "
        f"pourquoi {age} + cette durée dépasse l'espérance de vie à la naissance.",
        repo.millesime("esperance_vie_fr_65_eurostat") if age == 65
        else repo.millesime("esperance_vie_fr_insee"),
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
