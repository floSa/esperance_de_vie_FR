import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from common import (
    COLOR_DECEDES,
    COLOR_VIVANTS_ZONE,
    CURRENT_YEAR,
    SEX_COLORS,
    SEX_LABELS,
    apply_layout,
    download_csv,
    fr_num,
    get_cohort_survival,
    note_lecture,
    persist,
    render_sidebar,
    source_note,
)

st.set_page_config(page_title="Survie à un âge donné · Espérance de vie",
                   page_icon="🔄", layout="wide")
render_sidebar()

st.title("🔄 Survie à un âge donné")
st.caption(
    "Part d'une génération encore en vie à un âge donné, et évolution de cette part "
    "d'une génération à l'autre."
)

# ---------------------------------------------------------------------------
# 1. Sélecteurs
# ---------------------------------------------------------------------------

persist("sexe", "femmes")
persist("age_fixe", 70)

col_sexe, col_age = st.columns([1, 3])
with col_sexe:
    sexe = st.selectbox(
        "Sexe", ["femmes", "hommes"],
        format_func=lambda s: SEX_LABELS[s], key="sexe",
    )
with col_age:
    age = st.select_slider(
        "Âge atteint", options=[35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 85, 90],
        key="age_fixe",
    )

# ---------------------------------------------------------------------------
# 2. Série : % encore en vie à `age` ans, par année d'observation
# ---------------------------------------------------------------------------


@st.cache_data
def build_fixed_age_series(sexe: str, age: int) -> pd.DataFrame:
    """Une ligne par année où une génération connue a atteint `age` ans.

    L'année maximale est bornée à l'année courante : une génération qui
    n'a pas encore atteint cet âge n'a rien à y faire.
    """
    rows = []
    for year in range(1930 + age, min(CURRENT_YEAR, 1990 + age) + 1):
        naissance = year - age
        pct = get_cohort_survival(sexe, naissance, age)
        if pct is not None:
            rows.append({"annee": year, "naissance": naissance, "vivants_pct": pct})
    df = pd.DataFrame(rows)
    df["decedes_pct"] = 100 - df["vivants_pct"]
    return df


df = build_fixed_age_series(sexe, age)
an_debut, an_fin = int(df["annee"].iloc[0]), int(df["annee"].iloc[-1])
pct_debut, pct_fin = float(df["vivants_pct"].iloc[0]), float(df["vivants_pct"].iloc[-1])
gain = pct_fin - pct_debut

# ---------------------------------------------------------------------------
# 3. Chiffres clés
# ---------------------------------------------------------------------------

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Âge atteint", f"{age} ans",
          help="Âge sélectionné avec le curseur ci-dessus")
c2.metric(
    f"Génération {an_debut - age}",
    f"{fr_num(pct_debut)} %",
    help=f"Part encore en vie quand cette génération a eu {age} ans, en {an_debut}",
)
c3.metric(
    f"Génération {an_fin - age}",
    f"{fr_num(pct_fin)} %",
    help=f"Part encore en vie quand cette génération a eu {age} ans, en {an_fin}",
)
c4.metric("Progression", f"+{fr_num(gain)} points")
c5.metric("Générations comparées", f"{an_debut - age} → {an_fin - age}")

st.markdown(
    f"> Part encore en vie à {age} ans : **{fr_num(pct_debut)} %** pour la génération "
    f"{an_debut - age}, **{fr_num(pct_fin)} %** pour la génération {an_fin - age}."
)

# ---------------------------------------------------------------------------
# 4. Graphique
# ---------------------------------------------------------------------------

y_min_axe = max(0.0, float(df["vivants_pct"].min()) - 5)

fig = go.Figure()
fig.add_trace(go.Scatter(
    x=df["annee"], y=df["vivants_pct"],
    fill="tozeroy", fillcolor=COLOR_VIVANTS_ZONE,
    line=dict(color=SEX_COLORS[sexe], width=2.5),
    name=f"Encore en vie à {age} ans",
    customdata=df["naissance"],
    hovertemplate=(
        "En %{x}, la génération née en %{customdata}<br>"
        f"atteint {age} ans : <b>%{{y:.1f}} %</b> encore en vie<extra></extra>"
    ),
))
fig.add_trace(go.Scatter(
    x=df["annee"], y=[100] * len(df),
    fill="tonexty", fillcolor=COLOR_DECEDES,
    line=dict(width=0),
    name=f"Décédés avant {age} ans",
    customdata=df["decedes_pct"],
    hovertemplate="%{customdata:.1f} % décédés<extra></extra>",
))
fig.add_annotation(
    x=an_fin, y=pct_fin, ax=an_debut, ay=pct_debut,
    axref="x", ayref="y",
    text=f"<b>+{fr_num(gain)} points</b>",
    showarrow=True, arrowhead=3, arrowwidth=2,
    arrowcolor=SEX_COLORS[sexe],
    font=dict(color=SEX_COLORS[sexe], size=14),
)
fig.update_yaxes(range=[y_min_axe, 100.5],
                 title=f"% de la génération encore en vie à {age} ans")
fig.update_xaxes(title=f"Année où la génération a atteint {age} ans")
apply_layout(
    fig, height=520,
    legend=dict(orientation="h", yanchor="bottom", y=1.05, x=0),
    title=f"{SEX_LABELS[sexe]} — part de la génération encore en vie à {age} ans",
)
st.plotly_chart(fig, width='stretch')

note_lecture(
    f"<strong>Axe horizontal</strong> : année où chaque génération atteint {age} ans. "
    f"{an_debut} correspond à la génération {an_debut - age}, {an_fin} à la "
    f"génération {an_fin - age}."
    "<br>"
    f"<strong>Axe vertical</strong> : part de la génération encore en vie à {age} ans, "
    "à partir d'une valeur non nulle pour rendre l'écart lisible."
    "<br>"
    f"<strong>Zones</strong> : en gris, survivants ; en rouge, décès avant {age} ans."
    "<br><br>"
    "Un point par génération : les personnes diffèrent d'un point à l'autre."
    "<br>"
    f"{SEX_LABELS[sexe]} : <strong>{fr_num(pct_debut)} %</strong> de la génération "
    f"{an_debut - age} en vie à {age} ans, <strong>{fr_num(pct_fin)} %</strong> de la "
    f"génération {an_fin - age}.",
    "Survie par génération : estimation à ±5 % (tables de génération INSEE / "
    "Vallin & Meslé)",
)

download_csv(df, "survie_age_donne")
source_note()
