import os

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from common import (
    COLOR_E0,
    SEX_COLORS,
    SEX_LABELS,
    SEX_ZONES,
    apply_layout,
    download_csv,
    persist,
    render_sidebar,
    source_note,
)
from data.embedded import PERIOD_DISTRIBUTION_FEMMES, PERIOD_DISTRIBUTION_HOMMES
from data.loader import compute_percentiles_from_hmd, download_hmd_table, parse_hmd_text

st.set_page_config(page_title="Distribution & variance · Espérance de vie", page_icon="📐", layout="wide")
render_sidebar()

st.title("📐 Distribution des âges au décès — Compression de la mortalité")

persist("sexe", "femmes")
sexe = st.radio(
    "Sexe",
    ["femmes", "hommes"],
    format_func=lambda s: SEX_LABELS[s],
    horizontal=True,
    key="sexe",
)


@st.cache_data
def build_distribution(sexe: str) -> pd.DataFrame:
    dist = PERIOD_DISTRIBUTION_FEMMES if sexe == "femmes" else PERIOD_DISTRIBUTION_HOMMES
    return pd.DataFrame(dist)


df = build_distribution(sexe)
main_color = SEX_COLORS[sexe]
zone_color = SEX_ZONES[sexe]

# ---------------------------------------------------------------------------
# 1. Bande Q1–Q3, médiane et e0
# ---------------------------------------------------------------------------

fig = go.Figure()
fig.add_trace(go.Scatter(
    x=df["year"], y=df["q1"],
    line=dict(width=0), showlegend=False, hoverinfo="skip", name="Q1",
))
fig.add_trace(go.Scatter(
    x=df["year"], y=df["q3"],
    fill="tonexty", fillcolor=zone_color,
    line=dict(width=0), name="Zone Q1–Q3",
    hovertemplate="Q3 : %{y} ans<extra></extra>",
))
fig.add_trace(go.Scatter(
    x=df["year"], y=df["median"],
    line=dict(color=main_color, width=3), name="Âge médian au décès (P50)",
    hovertemplate="Médiane : %{y} ans<extra></extra>",
))
fig.add_trace(go.Scatter(
    x=df["year"], y=df["e0"],
    line=dict(color=COLOR_E0, width=2, dash="dash"), name="Espérance de vie e₀",
    hovertemplate="e₀ : %{y} ans<extra></extra>",
))
for x, txt in ((1940, "WWII"), (2020, "Covid")):
    fig.add_vline(x=x, line_dash="dot", line_color="gray", opacity=0.5)
    fig.add_annotation(x=x, y=1.04, yref="paper", text=txt, showarrow=False, font=dict(size=11))
fig.add_annotation(
    x=1978, y=32, text="Compression de la mortalité →",
    showarrow=False, font=dict(size=13, color=main_color),
)
fig.update_yaxes(range=[0, 100], title="Âge (ans)")
fig.update_xaxes(title="Année")
apply_layout(fig, height=520, legend=dict(orientation="h", yanchor="bottom", y=1.08, x=0),
             title=f"Distribution des âges au décès — {SEX_LABELS[sexe]}")
st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------------------------------
# 2. Évolution de l'IQR
# ---------------------------------------------------------------------------

iqr_debut = int(df["iqr"].iloc[0])
iqr_fin = int(df["iqr"].iloc[-1])

fig_iqr = px.area(
    df, x="year", y="iqr",
    labels={"year": "Année", "iqr": "IQR = Q3 − Q1 (ans)"},
)
fig_iqr.update_traces(line_color=main_color, fillcolor=zone_color, line_width=2)
fig_iqr.add_annotation(x=df["year"].iloc[0], y=iqr_debut, text=f"<b>{iqr_debut} ans</b>",
                       showarrow=False, yshift=14, xshift=18, font=dict(color=main_color, size=14))
fig_iqr.add_annotation(x=df["year"].iloc[-1], y=iqr_fin, text=f"<b>{iqr_fin} ans</b>",
                       showarrow=False, yshift=14, xshift=-14, font=dict(color=main_color, size=14))
apply_layout(fig_iqr, height=320,
             title="Écart interquartile (IQR — intervalle contenant 50 % des décès)")
st.plotly_chart(fig_iqr, use_container_width=True)

st.info(
    f"**Interprétation clé** : l'écart Q3−Q1 est passé de **{iqr_debut} ans (1900)** à "
    f"**{iqr_fin} ans (2025)** chez les {SEX_LABELS[sexe].lower()} : la mortalité s'est "
    "**comprimée** autour d'un âge élevé. En 1900, mourir à 5 ans ou à 75 ans était "
    "également banal ; aujourd'hui les décès se concentrent dans une fenêtre étroite "
    "au-delà de 70 ans."
)

# ---------------------------------------------------------------------------
# 3. Données HMD réelles (optionnel)
# ---------------------------------------------------------------------------

st.subheader("📥 Données HMD réelles (optionnel)")
st.caption(
    "Importez une table de mortalité période 1x1 France issue de mortality.org "
    "(fltper_1x1.txt pour les femmes, mltper_1x1.txt pour les hommes) pour "
    "recalculer les vrais quartiles et l'écart-type, superposés aux estimations."
)


@st.cache_data
def hmd_percentiles_from_text(text: str) -> pd.DataFrame | None:
    df_hmd = parse_hmd_text(text)
    if df_hmd is None or "dx" not in df_hmd.columns:
        return None
    return compute_percentiles_from_hmd(df_hmd)


hmd_result = None
hmd_label = None

uploaded = st.file_uploader(
    "Fichier HMD (fltper_1x1.txt ou mltper_1x1.txt)", type=["txt"], key="hmd_upload"
)
if uploaded is not None:
    hmd_result = hmd_percentiles_from_text(uploaded.read().decode("utf-8", errors="replace"))
    hmd_label = uploaded.name
    if hmd_result is None:
        st.error("Fichier illisible — attendu : table HMD 1x1 avec colonnes Year, Age, dx, ex.")

hmd_user = os.environ.get("HMD_USER")
hmd_pwd = os.environ.get("HMD_PASSWORD")
if hmd_user and hmd_pwd and hmd_result is None:
    if st.button(f"Télécharger la table {SEX_LABELS[sexe].lower()} depuis mortality.org"):
        with st.spinner("Téléchargement HMD…"):
            df_dl = download_hmd_table(sexe[0], hmd_user, hmd_pwd)
        if df_dl is not None:
            hmd_result = compute_percentiles_from_hmd(df_dl)
            hmd_label = f"HMD direct ({SEX_LABELS[sexe].lower()})"
        else:
            st.error("Téléchargement HMD impossible — vérifiez les credentials.")
elif not (hmd_user and hmd_pwd):
    st.caption(
        "💡 Astuce : définissez `HMD_USER` et `HMD_PASSWORD` (inscription gratuite "
        "sur mortality.org) pour télécharger les tables sans passer par l'upload."
    )

if hmd_result is not None and len(hmd_result):
    hmd_df = hmd_result[hmd_result["year"] >= 1900].copy()
    fig_cmp = go.Figure()
    fig_cmp.add_trace(go.Scatter(
        x=hmd_df["year"], y=hmd_df["q1"],
        line=dict(width=0), showlegend=False, hoverinfo="skip",
    ))
    fig_cmp.add_trace(go.Scatter(
        x=hmd_df["year"], y=hmd_df["q3"],
        fill="tonexty", fillcolor=zone_color, line=dict(width=0),
        name="Zone Q1–Q3 (HMD réel)",
    ))
    fig_cmp.add_trace(go.Scatter(
        x=hmd_df["year"], y=hmd_df["median"],
        line=dict(color=main_color, width=2.5), name="Médiane (HMD réel)",
    ))
    fig_cmp.add_trace(go.Scatter(
        x=df["year"], y=df["median"],
        line=dict(color="gray", width=2, dash="dash"), name="Médiane (estimation embarquée)",
    ))
    fig_cmp.add_trace(go.Scatter(
        x=hmd_df["year"], y=hmd_df["sd"],
        line=dict(color=COLOR_E0, width=2, dash="dot"), name="Écart-type des âges au décès (HMD)",
    ))
    fig_cmp.update_yaxes(title="Âge / années")
    fig_cmp.update_xaxes(title="Année")
    apply_layout(fig_cmp, height=520, legend=dict(orientation="h", yanchor="bottom", y=1.08, x=0),
                 title=f"Quartiles réels vs estimés — {hmd_label}")
    st.plotly_chart(fig_cmp, use_container_width=True)
    st.success("Courbes recalculées depuis la vraie distribution dx de la table HMD.")

download_csv(df, "distribution_variance")
source_note()
