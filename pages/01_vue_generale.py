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
# Toujours Eurostat : c'est la seule source qui couvre les 96 âges sur une
# période identique. Mélanger avec l'INSEE ferait changer l'axe des années
# selon l'âge choisi, et deux sélections ne seraient plus comparables.
serie = repo.serie_par_sexe(age, source="eurostat")
an_debut, an_fin = repo.periode_comparable()
y_label = ("Espérance de vie à la naissance (ans)" if age == 0
           else f"Années restant à vivre à {age} ans")

# ---------------------------------------------------------------------------
# 2. Métriques de l'âge sélectionné
# ---------------------------------------------------------------------------

derniere = serie.iloc[-1]
premiere = serie.iloc[0]
an_premier = int(premiere["year"])
gain_f = float(derniere["femmes"] - premiere["femmes"])

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric(
    "Âge observé",
    "Naissance" if age == 0 else f"{age} ans",
    help="Âge sélectionné avec le curseur ci-dessus",
)
c2.metric(f"Femmes, {an_fin}", f"{fr_num(derniere['femmes'])} ans")
c3.metric(f"Hommes, {an_fin}", f"{fr_num(derniere['hommes'])} ans")
c4.metric("Écart femmes − hommes",
          f"{fr_num(derniere['femmes'] - derniere['hommes'])} ans")
c5.metric(f"Gain femmes depuis {an_premier}", f"+{fr_num(gain_f)} ans")

if age == 0:
    st.caption(
        f"En {an_fin}, une fille qui naît vivra **{fr_num(derniere['femmes'])} "
        f"ans** en moyenne. Un garçon, **{fr_num(derniere['hommes'])} ans**."
    )
else:
    st.caption(
        f"En {an_fin}, une femme de {age} ans vivra encore "
        f"**{fr_num(derniere['femmes'])} ans** en moyenne. "
        f"Elle mourra donc vers **{fr_num(age + derniere['femmes'], 0)} ans**."
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
fig.update_yaxes(title=y_label)
fig.update_xaxes(title="Année", range=[an_debut - 1, an_fin + 1])
apply_layout(fig, height=440,
             legend=dict(orientation="h", yanchor="bottom", y=1.08, x=0),
             title=f"Espérance de vie à {libelle_age} — {an_debut} à {an_fin}")
st.plotly_chart(fig, width='stretch')

exemple = round(float(derniere["femmes"]))
if age == 0:
    quoi = ("Le nombre d'années que vivra un bébé né cette année-là, "
            "si la mortalité ne change plus.")
    piege = ("Ce n'est pas une prévision. C'est une photo de la mortalité "
             "de l'année.")
else:
    quoi = (f"Le nombre d'années qu'il reste à vivre à une personne de "
            f"{age} ans cette année-là.")
    piege = (f"C'est une durée, pas un âge. Un point à {exemple} veut dire "
             f"« encore {exemple} ans à vivre », soit un décès vers "
             f"{age + exemple} ans.")

note_lecture(
    "<strong>Axe horizontal</strong> : les années, "
    f"de {an_debut} à {an_fin}."
    "<br>"
    "<strong>Axe vertical</strong> : " + quoi
    + "<br>"
    "<strong>Deux courbes</strong> : les femmes en rose, les hommes en bleu."
    "<br><br>"
    + piege
    + "<br><br>"
    f"L'axe des années ne bouge jamais : toujours {an_debut} à {an_fin}. "
    "Deux âges se comparent donc directement."
    + (
        f"<br>Eurostat ne publie cet âge qu'à partir de {an_premier} : la "
        "courbe démarre plus à droite."
        if an_premier > an_debut else ""
    ),
    repo.millesime("esperance_vie_fr_tous_ages_eurostat"),
)

# ---------------------------------------------------------------------------
# 4. Série historique (indépendante du curseur)
# ---------------------------------------------------------------------------

st.subheader("🕰️ Depuis 1816 — espérance de vie à la naissance")

fig_longue = go.Figure()
fig_longue.add_trace(go.Scatter(
    x=longue["year"], y=longue["esperance"],
    line=dict(color=COLOR_E0, width=2),
    name="Femmes et hommes réunis",
    hovertemplate="%{x} : %{y:.1f} ans<extra></extra>",
))
for an, txt in ((1871, "1871"), (1918, "1918"), (1940, "1940")):
    fig_longue.add_vline(x=an, line_dash="dot", line_color="gray", opacity=0.5)
    fig_longue.add_annotation(x=an, y=1.05, yref="paper", text=txt,
                              showarrow=False, font=dict(size=11))
fig_longue.update_yaxes(title="Espérance de vie à la naissance (ans)")
fig_longue.update_xaxes(title="Année")
apply_layout(fig_longue, height=380, showlegend=False,
             title="France, 1816–2023, femmes et hommes réunis")
st.plotly_chart(fig_longue, width='stretch')

note_lecture(
    "<strong>Ce graphique ne dépend pas du curseur.</strong>"
    "<br>"
    "Il montre toujours l'espérance de vie à la naissance, femmes et hommes "
    "réunis, de 1816 à 2023."
    "<br><br>"
    "Chaque creux est une crise de mortalité."
    "<br>"
    "1871 : guerre franco-prussienne. 1918 : grippe espagnole et fin de la "
    "Première Guerre. 1940 : Seconde Guerre."
    "<br><br>"
    "En 1918, la valeur tombe à <strong>34,8 ans</strong>, contre 43,0 "
    "l'année d'avant. Elle remonte dès l'année suivante.",
    repo.millesime("esperance_vie_fr_longue_owid"),
)

# ---------------------------------------------------------------------------
# 5. Comparaison européenne
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
