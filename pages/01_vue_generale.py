import pandas as pd
import plotly.express as px
import streamlit as st

from common import (
    COLOR_E0,
    COLOR_FEMMES,
    COLOR_HOMMES,
    SEX_LABELS,
    apply_layout,
    download_csv,
    fr_num,
    render_sidebar,
    source_note,
)
from data.embedded import (
    E60_SERIES,
    E65_SERIES,
    PERIOD_DISTRIBUTION_FEMMES,
    PERIOD_DISTRIBUTION_HOMMES,
)
from data.european import EU_LIFE_EXPECTANCY_2024
from data.loader import eurostat_to_embedded_format, fetch_eurostat_life_expectancy

st.set_page_config(page_title="Vue générale · Espérance de vie", page_icon="📈", layout="wide")
render_sidebar()

st.title("📈 Vue générale — France 1900–2025")

# ---------------------------------------------------------------------------
# Données
# ---------------------------------------------------------------------------

@st.cache_data
def build_series() -> pd.DataFrame:
    rows = []
    for sexe, dist in (("femmes", PERIOD_DISTRIBUTION_FEMMES), ("hommes", PERIOD_DISTRIBUTION_HOMMES)):
        for rec in dist:
            y = rec["year"]
            rows.append({
                "year": y,
                "sexe": SEX_LABELS[sexe],
                "e0": rec["e0"],
                "e60": E60_SERIES[sexe][y],
                "e65": E65_SERIES[sexe][y],
            })
    return pd.DataFrame(rows)


df = build_series()
f_last = PERIOD_DISTRIBUTION_FEMMES[-1]
h_last = PERIOD_DISTRIBUTION_HOMMES[-1]
f_first = PERIOD_DISTRIBUTION_FEMMES[0]
h_first = PERIOD_DISTRIBUTION_HOMMES[0]

# ---------------------------------------------------------------------------
# 1. Métriques
# ---------------------------------------------------------------------------

gain = ((f_last["e0"] - f_first["e0"]) + (h_last["e0"] - h_first["e0"])) / 2
c1, c2, c3, c4 = st.columns(4)
c1.metric("e₀ femmes 2025", f"{fr_num(f_last['e0'])} ans")
c2.metric("e₀ hommes 2025", f"{fr_num(h_last['e0'])} ans")
c3.metric("Écart F/H", f"{fr_num(f_last['e0'] - h_last['e0'])} ans")
c4.metric("Gain depuis 1900", f"+{fr_num(gain)} ans", help="Moyenne des gains femmes et hommes")

# ---------------------------------------------------------------------------
# 2. Évolution 1900–2025
# ---------------------------------------------------------------------------

INDICATEURS = {
    "Espérance de vie à la naissance": ("e0", "Espérance de vie à la naissance (ans)"),
    "Espérance de vie à 60 ans": ("e60", "Espérance de vie résiduelle à 60 ans (ans)"),
    "Espérance de vie à 65 ans": ("e65", "Espérance de vie résiduelle à 65 ans (ans)"),
}
choix = st.radio("Indicateur", list(INDICATEURS), horizontal=True, key="indicateur_page1")
col, y_label = INDICATEURS[choix]

fig = px.line(
    df,
    x="year",
    y=col,
    color="sexe",
    markers=True,
    color_discrete_map={"Femmes": COLOR_FEMMES, "Hommes": COLOR_HOMMES},
    labels={"year": "Année", col: y_label, "sexe": ""},
)
fig.update_traces(line_width=2, marker_size=6)
for x, txt in ((1918, "WWI 1918"), (1945, "WWII 1945"), (2020, "Covid 2020")):
    fig.add_vline(x=x, line_dash="dot", line_color="gray", opacity=0.5)
    fig.add_annotation(x=x, y=1.04, yref="paper", text=txt, showarrow=False, font=dict(size=11))
apply_layout(fig, height=480, legend=dict(orientation="h", yanchor="bottom", y=1.08, x=0))
if col == "e60" or col == "e65":
    st.caption("Nombre d'années restant à vivre à cet âge, selon la table du moment de chaque année.")
st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------------------------------
# 3. Comparaison européenne
# ---------------------------------------------------------------------------

st.subheader("🇪🇺 Comparaison européenne")

with st.expander("🔄 Rafraîchir via l'API Eurostat (demo_mlexpec, sans authentification)"):
    annee_api = st.selectbox("Année", [2024, 2023, 2022], index=0, key="annee_api_eurostat")
    if st.button("Interroger l'API"):
        with st.spinner("Requête Eurostat en cours…"):
            raw = fetch_eurostat_life_expectancy(annee_api)
        refreshed = eurostat_to_embedded_format(raw) if raw is not None and len(raw) else []
        if refreshed:
            st.session_state["eu_data"] = refreshed
            st.session_state["eu_year"] = annee_api
            st.success(f"{len(refreshed)} pays rafraîchis depuis Eurostat ({annee_api}).")
        else:
            st.warning("API Eurostat injoignable ou réponse vide — données embarquées conservées.")

eu_data = st.session_state.get("eu_data")
eu_year = st.session_state.get("eu_year", 2024)
eu_source = "données embarquées (Eurostat 2024)"
if eu_data is None:
    eu_data = EU_LIFE_EXPECTANCY_2024
else:
    eu_source = f"API Eurostat, année {eu_year}"

eu_df = pd.DataFrame(eu_data)
eu_avg_row = eu_df[eu_df["code"] == "EU"]
eu_avg = float(eu_avg_row["e0_total"].iloc[0]) if len(eu_avg_row) else None
pays_df = eu_df[eu_df["code"] != "EU"].dropna(subset=["e0_total"]).copy()
pays_df = pays_df.sort_values("e0_total", ascending=False)

fig_eu = px.bar(
    pays_df,
    x="e0_total",
    y="country",
    orientation="h",
    color="e0_total",
    color_continuous_scale="Blues",
    labels={"e0_total": "Espérance de vie totale (ans)", "country": ""},
)
fig_eu.update_traces(
    marker_line_color=COLOR_E0,
    marker_line_width=[2.5 if c == "FR" else 0 for c in pays_df["code"]],
)
fig_eu.update_yaxes(categoryorder="total ascending")
fig_eu.update_xaxes(range=[70, 86])
if eu_avg is not None:
    fig_eu.add_vline(
        x=eu_avg,
        line_dash="dash",
        line_color=COLOR_E0,
        annotation_text=f"Moyenne UE-27 : {fr_num(eu_avg)} ans",
        annotation_position="top left",
    )
fr_row = pays_df[pays_df["code"] == "FR"]
if len(fr_row):
    fig_eu.add_annotation(
        x=float(fr_row["e0_total"].iloc[0]),
        y="France",
        text="🇫🇷 France",
        showarrow=True,
        arrowhead=2,
        ax=45,
        ay=0,
        font=dict(color=COLOR_E0, size=13),
    )
apply_layout(fig_eu, height=680, coloraxis_showscale=False)
st.plotly_chart(fig_eu, use_container_width=True)
st.caption(f"Source affichée : {eu_source}. La France est encadrée en orange.")

# ---------------------------------------------------------------------------
# 4. Tableaux récapitulatifs
# ---------------------------------------------------------------------------

pays_df["ecart_fh"] = pays_df["e0_f"] - pays_df["e0_m"]
col_g, col_d = st.columns(2)
fmt = {
    "e0_f": st.column_config.NumberColumn("e₀ femmes", format="%.1f"),
    "e0_m": st.column_config.NumberColumn("e₀ hommes", format="%.1f"),
    "e0_total": st.column_config.NumberColumn("e₀ total", format="%.1f"),
    "ecart_fh": st.column_config.NumberColumn("Écart F−H", format="%.1f"),
    "country": st.column_config.TextColumn("Pays"),
}
with col_g:
    st.markdown("**Top 10 — e₀ femmes le plus élevé**")
    st.dataframe(
        pays_df.nlargest(10, "e0_f")[["country", "e0_f", "e0_m", "e0_total"]],
        column_config=fmt,
        hide_index=True,
        use_container_width=True,
    )
with col_d:
    st.markdown("**Top 10 — écart femmes/hommes le plus important**")
    st.dataframe(
        pays_df.nlargest(10, "ecart_fh")[["country", "ecart_fh", "e0_f", "e0_m"]],
        column_config=fmt,
        hide_index=True,
        use_container_width=True,
    )

download_csv(df, "vue_generale")
source_note()
