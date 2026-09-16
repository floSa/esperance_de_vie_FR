"""Accès aux sources de données publiques (INSEE, Eurostat, OWID, HMD).

Chaque fonction `fetch_*` retourne `(DataFrame, provenance)` où `provenance`
documente l'URL exacte, les paramètres et le millésime du jeu source — c'est
ce qui alimente le manifeste de `data/sources/manifest.json`.

Toutes les erreurs remontent en `SourceError` : aucune source n'échoue en
silence, sinon un rafraîchissement partiel passerait inaperçu.
"""

from __future__ import annotations

import io
from datetime import UTC, datetime

import numpy as np
import pandas as pd
import requests

USER_AGENT = "esperance-vie-app/0.1 (+https://github.com/floSa)"
TIMEOUT = 90

INSEE_MELODI = "https://api.insee.fr/melodi/data"
EUROSTAT = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data"
OWID_LIFE_EXPECTANCY = "https://ourworldindata.org/grapher/life-expectancy.csv"
HMD_LOGIN = "https://www.mortality.org/Account/Login"
HMD_FILE = "https://www.mortality.org/File/GetDocument/hmd.v6/FRATNP/STATS"

# France métropolitaine — périmètre constant sur toute la profondeur historique,
# contrairement à « France entière » qui intègre les DOM à partir de 1990.
INSEE_GEO_FM = "2025-FRANCE-FM"


class SourceError(RuntimeError):
    """Une source n'a pas pu être lue, ou a renvoyé autre chose que ses données."""


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _get(url: str, params: dict | None = None) -> requests.Response:
    try:
        r = requests.get(url, params=params, timeout=TIMEOUT,
                         headers={"User-Agent": USER_AGENT})
    except requests.RequestException as e:
        raise SourceError(f"{url} injoignable : {e}") from e
    if r.status_code != 200:
        raise SourceError(f"{url} → HTTP {r.status_code}")
    return r


# ---------------------------------------------------------------------------
# INSEE — API Melodi (ouverte, sans jeton)
# ---------------------------------------------------------------------------

def _melodi_all(dataset: str, params: dict) -> list[dict]:
    """Pagine un jeu Melodi jusqu'à épuisement des observations."""
    out: list[dict] = []
    page = 1
    while True:
        r = _get(f"{INSEE_MELODI}/{dataset}",
                 {**params, "maxResult": 1000, "page": page})
        try:
            obs = r.json().get("observations", [])
        except ValueError as e:
            raise SourceError(f"Melodi {dataset} : réponse non-JSON") from e
        if not obs:
            break
        out.extend(obs)
        page += 1
        if page > 50:
            raise SourceError(f"Melodi {dataset} : pagination anormalement longue")
    if not out:
        raise SourceError(f"Melodi {dataset} : aucune observation pour {params}")
    return out


def _melodi_frame(obs: list[dict]) -> pd.DataFrame:
    return pd.DataFrame([
        {**o["dimensions"], "value": o["measures"]["OBS_VALUE_NIVEAU"]["value"]}
        for o in obs
    ])


def fetch_insee_life_expectancy() -> tuple[pd.DataFrame, dict]:
    """Espérance de vie française par sexe et âge exact, séries longues INSEE.

    Âges disponibles : 0, 1, 20, 40, 60 ans. L'âge 65 n'est pas publié dans
    cette série — il vient d'Eurostat (`fetch_eurostat_life_expectancy_fr`).
    """
    params = {"FREQ": "A", "EC_MEASURE": "LEXPEC", "GEO": INSEE_GEO_FM}
    df = _melodi_frame(_melodi_all("DS_DECES_MORTALITE_SERIES", params))

    df = df[df["SEX"].isin(["F", "M"])].copy()
    df["age"] = df["AGE"].str.removeprefix("Y").astype(int)
    df["year"] = df["TIME_PERIOD"].astype(int)
    df["sexe"] = df["SEX"].map({"F": "femmes", "M": "hommes"})
    out = (df[["year", "sexe", "age", "value"]]
           .rename(columns={"value": "esperance"})
           .sort_values(["sexe", "age", "year"])
           .reset_index(drop=True))

    return out, {
        "libelle": "Espérance de vie par sexe et âge — France métropolitaine",
        "fournisseur": "INSEE",
        "jeu": "DS_DECES_MORTALITE_SERIES (EC_MEASURE=LEXPEC)",
        "url": f"{INSEE_MELODI}/DS_DECES_MORTALITE_SERIES",
        "parametres": params,
        "annees": f"{out['year'].min()}–{out['year'].max()}",
        "ages": sorted(out["age"].unique().tolist()),
        "lignes": len(out),
        "extrait_le": _now(),
    }


def fetch_insee_births() -> tuple[pd.DataFrame, dict]:
    """Naissances vivantes annuelles, France métropolitaine.

    Mesure retenue : lieu d'enregistrement (`LVB_PLACE_REG`), qui couvre
    1901–2025 sans rupture. La variante « lieu de résidence » ne commence
    qu'en 1975 : la mélanger introduirait une discontinuité en plein milieu
    des cohortes étudiées.
    """
    params = {"FREQ": "A", "EC_MEASURE": "LVB_PLACE_REG", "GEO": INSEE_GEO_FM}
    df = _melodi_frame(_melodi_all("DS_NAISSANCES_FECONDITE_SERIES", params))

    df["year"] = df["TIME_PERIOD"].astype(int)
    # Une même année peut porter plusieurs millésimes de publication ;
    # on retient la valeur la plus récemment révisée.
    out = (df.groupby("year", as_index=False)["value"].last()
             .rename(columns={"value": "naissances"})
             .sort_values("year")
             .reset_index(drop=True))
    out["naissances"] = out["naissances"].astype(int)

    return out, {
        "libelle": "Naissances vivantes annuelles — France métropolitaine",
        "fournisseur": "INSEE",
        "jeu": "DS_NAISSANCES_FECONDITE_SERIES (EC_MEASURE=LVB_PLACE_REG)",
        "url": f"{INSEE_MELODI}/DS_NAISSANCES_FECONDITE_SERIES",
        "parametres": params,
        "annees": f"{out['year'].min()}–{out['year'].max()}",
        "lignes": len(out),
        "extrait_le": _now(),
    }


# ---------------------------------------------------------------------------
# Our World in Data — profondeur historique (relais HMD, licence CC-BY)
# ---------------------------------------------------------------------------

def fetch_owid_life_expectancy() -> tuple[pd.DataFrame, dict]:
    """Espérance de vie à la naissance, France, tous sexes confondus.

    Seule source ouverte couvrant l'avant-1946 en continu : c'est elle qui
    fait apparaître les creux de 1918 et 1940, absents des séries INSEE.
    """
    r = _get(OWID_LIFE_EXPECTANCY)
    df = pd.read_csv(io.StringIO(r.text))
    fr = df[df["Code"] == "FRA"].copy()
    if fr.empty:
        raise SourceError("OWID : aucune ligne pour la France (schéma modifié ?)")

    value_col = [c for c in fr.columns if "expectancy" in c.lower()]
    if not value_col:
        raise SourceError(f"OWID : colonne espérance introuvable dans {list(fr.columns)}")

    out = (fr[["Year", value_col[0]]]
           .rename(columns={"Year": "year", value_col[0]: "esperance"})
           .sort_values("year")
           .reset_index(drop=True))
    out["esperance"] = out["esperance"].round(2)

    return out, {
        "libelle": "Espérance de vie à la naissance, France, tous sexes — séries longues",
        "fournisseur": "Our World in Data (d'après HMD et ONU)",
        "jeu": "grapher/life-expectancy",
        "url": OWID_LIFE_EXPECTANCY,
        "parametres": {"filtre": "Code == FRA"},
        "annees": f"{out['year'].min()}–{out['year'].max()}",
        "lignes": len(out),
        "extrait_le": _now(),
    }


# ---------------------------------------------------------------------------
# Eurostat — API JSON-stat (ouverte)
# ---------------------------------------------------------------------------

def _jsonstat(dataset: str, params: dict) -> tuple[pd.DataFrame, str]:
    """Décode une réponse JSON-stat 2.0 en DataFrame long.

    Retourne aussi la date de mise à jour déclarée par Eurostat, qui sert de
    millésime dans le manifeste.
    """
    r = _get(f"{EUROSTAT}/{dataset}", {**params, "format": "JSON"})
    try:
        js = r.json()
    except ValueError as e:
        raise SourceError(f"Eurostat {dataset} : réponse non-JSON") from e
    if not js.get("value"):
        raise SourceError(f"Eurostat {dataset} : aucune valeur pour {params}")

    ids, sizes, dims = js["id"], js["size"], js["dimension"]
    labels = {
        d: {pos: code for code, pos in dims[d]["category"]["index"].items()}
        for d in ids
    }
    strides = [1] * len(sizes)
    for i in range(len(sizes) - 2, -1, -1):
        strides[i] = strides[i + 1] * sizes[i + 1]

    rows = []
    for key, value in js["value"].items():
        idx = int(key)
        rec = {d: labels[d][(idx // strides[i]) % sizes[i]] for i, d in enumerate(ids)}
        rec["value"] = value
        rows.append(rec)
    return pd.DataFrame(rows), js.get("updated", "?")


def fetch_eurostat_life_expectancy_fr() -> tuple[pd.DataFrame, dict]:
    """Espérance de vie française par sexe, pour **tous les âges** de 0 à 95 ans.

    L'INSEE ne publie que cinq âges (0, 1, 20, 40, 60) mais remonte à 1946 ;
    Eurostat publie les 96 âges mais seulement depuis 1998. Les deux séries se
    complètent : profondeur historique d'un côté, finesse par âge de l'autre.
    """
    params = {"geo": "FR", "sex": ["F", "M"]}
    df, updated = _jsonstat("demo_mlexpec", params)

    df["age_num"] = pd.to_numeric(
        df["age"].str.replace("Y_LT1", "0", regex=False)
                 .str.replace("Y_GE95", "95", regex=False)
                 .str.removeprefix("Y"),
        errors="coerce",
    )
    df = df.dropna(subset=["age_num", "value"])

    out = (df.assign(year=df["time"].astype(int),
                     sexe=df["sex"].map({"F": "femmes", "M": "hommes"}),
                     age=df["age_num"].astype(int))
             .rename(columns={"value": "esperance"})
             [["year", "sexe", "age", "esperance"]]
             .sort_values(["sexe", "age", "year"])
             .reset_index(drop=True))

    return out, {
        "libelle": "Espérance de vie par sexe et âge exact (0 à 95 ans), France",
        "fournisseur": "Eurostat",
        "jeu": "demo_mlexpec",
        "url": f"{EUROSTAT}/demo_mlexpec",
        "parametres": params,
        "millesime_source": updated,
        "annees": f"{out['year'].min()}–{out['year'].max()}",
        "ages": f"{out['age'].min()}–{out['age'].max()}",
        "lignes": len(out),
        "extrait_le": _now(),
    }


def fetch_eurostat_europe(year: int | None = None) -> tuple[pd.DataFrame, dict]:
    """Comparaison européenne de l'espérance de vie à la naissance.

    Sans `year`, retient automatiquement la dernière année réellement peuplée :
    Eurostat publie l'année courante dans ses dimensions bien avant d'y mettre
    des valeurs.
    """
    params = {"age": "Y_LT1", "sex": ["F", "M", "T"]}
    if year is not None:
        params["time"] = str(year)
    df, updated = _jsonstat("demo_mlexpec", params)

    df["year"] = df["time"].astype(int)
    retenue = int(year) if year is not None else int(df["year"].max())
    df = df[df["year"] == retenue]

    pivot = (df.pivot_table(index="geo", columns="sex", values="value")
               .reset_index()
               .rename(columns={"F": "e0_f", "M": "e0_m", "T": "e0_total"}))
    out = (pivot.dropna(subset=["e0_total"])
                .sort_values("e0_total", ascending=False)
                .reset_index(drop=True))
    out.insert(1, "annee", retenue)

    return out, {
        "libelle": f"Espérance de vie à la naissance par pays européen ({retenue})",
        "fournisseur": "Eurostat",
        "jeu": "demo_mlexpec",
        "url": f"{EUROSTAT}/demo_mlexpec",
        "parametres": {**params, "time": str(retenue)},
        "millesime_source": updated,
        "annee_retenue": retenue,
        "lignes": len(out),
        "extrait_le": _now(),
    }


def _quantiles_from_dx(ages: np.ndarray, dx: np.ndarray) -> dict:
    """Quartiles, IQR et écart-type de la distribution des âges au décès."""
    dx = np.maximum(dx, 0)
    total = dx.sum()
    if total <= 0:
        return {}
    w = dx / total
    cdf = np.cumsum(w)
    mean = float(np.average(ages, weights=w))
    q1, med, q3 = (float(ages[np.searchsorted(cdf, p)]) for p in (0.25, 0.50, 0.75))
    return {
        "q1": q1, "median": med, "q3": q3, "iqr": q3 - q1,
        "mean_age": round(mean, 2),
        "sd": round(float(np.sqrt(np.average((ages - mean) ** 2, weights=w))), 2),
    }


def fetch_eurostat_death_distribution() -> tuple[pd.DataFrame, dict]:
    """Quartiles réels des âges au décès, calculés depuis la table de mortalité.

    `dx` est le nombre de décès par âge de la table — la densité directe des
    âges au décès, donc la bonne base pour des quartiles.
    """
    params = {"geo": "FR", "indic_de": "NUMBERDYING", "sex": ["F", "M"]}
    df, updated = _jsonstat("demo_mlifetable", params)

    df["age_num"] = pd.to_numeric(
        df["age"].str.replace("Y_LT1", "0", regex=False)
                 .str.replace("Y_OPEN", "100", regex=False)
                 .str.removeprefix("Y"),
        errors="coerce",
    )
    df = df.dropna(subset=["age_num", "value"])

    rows = []
    for (year, sex), grp in df.groupby(["time", "sex"]):
        grp = grp.sort_values("age_num")
        stats = _quantiles_from_dx(grp["age_num"].to_numpy(float),
                                   grp["value"].to_numpy(float))
        if stats:
            rows.append({"year": int(year),
                         "sexe": {"F": "femmes", "M": "hommes"}[sex],
                         **stats})
    if not rows:
        raise SourceError("Eurostat demo_mlifetable : aucune distribution exploitable")

    out = pd.DataFrame(rows).sort_values(["sexe", "year"]).reset_index(drop=True)
    return out, {
        "libelle": "Distribution des âges au décès (quartiles, IQR, écart-type)",
        "fournisseur": "Eurostat",
        "jeu": "demo_mlifetable (indic_de=NUMBERDYING, soit dx)",
        "url": f"{EUROSTAT}/demo_mlifetable",
        "parametres": params,
        "millesime_source": updated,
        "annees": f"{out['year'].min()}–{out['year'].max()}",
        "lignes": len(out),
        "extrait_le": _now(),
    }


# ---------------------------------------------------------------------------
# HMD — nécessite un compte gratuit sur mortality.org
# ---------------------------------------------------------------------------

def hmd_session(email: str, password: str) -> requests.Session:
    """Ouvre une session authentifiée sur mortality.org.

    Le site est une application ASP.NET Core : l'authentification HTTP Basic
    n'est pas supportée (elle renvoie 200 + le formulaire de connexion), il
    faut poster le formulaire avec son jeton antiforgery.
    """
    s = requests.Session()
    s.headers.update({"User-Agent": USER_AGENT})

    page = s.get(HMD_LOGIN, timeout=TIMEOUT)
    if page.status_code != 200:
        raise SourceError(f"HMD : page de connexion inaccessible (HTTP {page.status_code})")

    token = None
    for line in page.text.splitlines():
        if "__RequestVerificationToken" in line and 'value="' in line:
            token = line.split('value="', 1)[1].split('"', 1)[0]
            break
    if token is None:
        raise SourceError("HMD : jeton antiforgery introuvable — formulaire modifié ?")

    resp = s.post(
        HMD_LOGIN,
        data={"Email": email, "Password": password,
              "__RequestVerificationToken": token, "ReturnUrl": "/"},
        timeout=TIMEOUT,
        allow_redirects=True,
    )
    if "Password" in resp.text and "Login" in resp.text[:2000]:
        raise SourceError("HMD : identifiants refusés (le formulaire est réaffiché)")
    return s


def fetch_hmd_life_table(sexe: str, session: requests.Session) -> tuple[pd.DataFrame, dict]:
    """Table de mortalité période France 1×1 (`fltper_1x1.txt` / `mltper_1x1.txt`).

    Couvre 1816→2023 par âge et par sexe : la seule source permettant de
    calculer les quartiles réels avant 2014.
    """
    filename = "fltper_1x1.txt" if sexe == "femmes" else "mltper_1x1.txt"
    url = f"{HMD_FILE}/{filename}"
    r = session.get(url, timeout=TIMEOUT)
    if r.status_code != 200:
        raise SourceError(f"HMD {filename} → HTTP {r.status_code}")
    if "text/html" in r.headers.get("content-type", ""):
        raise SourceError(
            f"HMD {filename} : le serveur a renvoyé une page HTML au lieu du "
            "fichier — session expirée ou non authentifiée."
        )

    df = pd.read_csv(io.StringIO(r.text), sep=r"\s+", skiprows=2, na_values=".")
    df.columns = df.columns.str.strip()
    if "dx" not in df.columns:
        raise SourceError(f"HMD {filename} : colonne dx absente ({list(df.columns)})")
    df["Age"] = pd.to_numeric(df["Age"].astype(str).str.replace("+", "", regex=False),
                              errors="coerce")
    df = df.dropna(subset=["Age", "dx"])

    rows = []
    for year, grp in df.groupby("Year"):
        grp = grp.sort_values("Age")
        stats = _quantiles_from_dx(grp["Age"].to_numpy(float), grp["dx"].to_numpy(float))
        if stats:
            rows.append({"year": int(year), "sexe": sexe, **stats})

    out = pd.DataFrame(rows).sort_values("year").reset_index(drop=True)
    return out, {
        "libelle": f"Distribution des âges au décès ({sexe}) — table HMD 1×1",
        "fournisseur": "Human Mortality Database",
        "jeu": f"FRATNP/STATS/{filename}",
        "url": url,
        "parametres": {"authentification": "compte mortality.org"},
        "annees": f"{out['year'].min()}–{out['year'].max()}",
        "lignes": len(out),
        "extrait_le": _now(),
    }
