import plotly.express as px
import streamlit as st

from common import (
    COLOR_E0,
    apply_layout,
    download_csv,
    fr_num,
    note_lecture,
    render_sidebar,
    source_note,
)
from data import repository as repo

st.set_page_config(page_title="Comparaison européenne · Espérance de vie",
                   page_icon="🇪🇺", layout="wide")
render_sidebar()

annee = repo.annee_europe()
pays = repo.europe()
moyenne = repo.moyenne_ue()
fr = pays[pays["code"] == "FR"].iloc[0]
rang = int(pays.index[pays["code"] == "FR"][0]) + 1

st.title("🇪🇺 Comparaison européenne")
st.caption(
    f"Espérance de vie à la naissance dans les 27 États membres de l'Union "
    f"européenne, en {annee}."
)

# ---------------------------------------------------------------------------
# 1. Chiffres clés
# ---------------------------------------------------------------------------

c1, c2, c3, c4 = st.columns(4)
c1.metric("France", f"{fr_num(fr['e0_total'])} ans")
c2.metric("Rang de la France", f"{rang}ᵉ sur {len(pays)}")
c3.metric("Moyenne UE-27", f"{fr_num(moyenne)} ans" if moyenne else "—")
c4.metric("En tête", f"{pays.iloc[0]['country']} — {fr_num(pays.iloc[0]['e0_total'])} ans")

# ---------------------------------------------------------------------------
# 2. Classement
# ---------------------------------------------------------------------------

fig = px.bar(
    pays, x="e0_total", y="country", orientation="h",
    color="e0_total", color_continuous_scale="Blues",
    labels={"e0_total": "Espérance de vie à la naissance (ans)", "country": ""},
)
fig.update_traces(
    marker_line_color=COLOR_E0,
    marker_line_width=[2.5 if c == "FR" else 0 for c in pays["code"]],
    hovertemplate="%{y} : %{x:.1f} ans<extra></extra>",
)
fig.update_yaxes(categoryorder="total ascending")
fig.update_xaxes(range=[70, 86])
if moyenne is not None:
    fig.add_vline(
        x=moyenne, line_dash="dash", line_color=COLOR_E0,
        annotation_text=f"Moyenne UE-27 : {fr_num(moyenne)} ans",
        annotation_position="top left",
    )
apply_layout(fig, height=680, coloraxis_showscale=False,
             title=f"Les 27 États membres en {annee}")
st.plotly_chart(fig, width='stretch')

note_lecture(
    "<strong>Une barre par pays</strong>, du plus élevé en haut au plus bas "
    "en bas. Femmes et hommes réunis."
    "<br>"
    "<strong>La France est cerclée d'orange.</strong> Elle arrive "
    f"<strong>{rang}<sup>e</sup> sur {len(pays)}</strong>."
    "<br>"
    "<strong>Le trait orange</strong> est la moyenne des 27 pays."
    "<br><br>"
    "Attention à l'échelle : elle démarre à 70 ans, pas à 0. Les barres "
    "paraissent donc très inégales. En réalité, les 27 pays tiennent en un "
    "peu plus de 8 ans."
    "<br><br>"
    f"Ce graphique montre <strong>une seule année, {annee}</strong>. Ce n'est "
    "pas une évolution.",
    repo.millesime("esperance_vie_europe_eurostat"),
)

# ---------------------------------------------------------------------------
# 3. Détail femmes / hommes
# ---------------------------------------------------------------------------

st.subheader("Détail par sexe")

fmt = {
    "country": st.column_config.TextColumn("Pays"),
    "e0_f": st.column_config.NumberColumn("Femmes", format="%.1f"),
    "e0_m": st.column_config.NumberColumn("Hommes", format="%.1f"),
    "e0_total": st.column_config.NumberColumn("Total", format="%.1f"),
    "ecart_fh": st.column_config.NumberColumn("Écart F−H", format="%.1f"),
}
col_g, col_d = st.columns(2)
with col_g:
    st.markdown("**Espérance de vie des femmes la plus élevée**")
    st.dataframe(pays.nlargest(10, "e0_f")[["country", "e0_f", "e0_m", "e0_total"]],
                 column_config=fmt, hide_index=True, width='stretch')
with col_d:
    st.markdown("**Écart femmes − hommes le plus important**")
    st.dataframe(pays.nlargest(10, "ecart_fh")[["country", "ecart_fh", "e0_f", "e0_m"]],
                 column_config=fmt, hide_index=True, width='stretch')

st.caption(
    "L'écart femmes − hommes est le plus fort dans les pays baltes, le plus "
    "faible aux Pays-Bas et en Suède. Il reflète surtout la surmortalité "
    "masculine aux âges actifs."
)

download_csv(pays, "comparaison_europe")
source_note()
