"""
Téléchargement des tables de mortalité complètes depuis HMD.
Nécessite une inscription gratuite sur mortality.org
et des credentials en variable d'environnement.

Variables d'environnement requises :
  HMD_USER=votre@email.com
  HMD_PASSWORD=motdepasse

Si les credentials ne sont pas disponibles, l'app utilise les données
embarquées dans embedded.py.

Fournit aussi un accès (sans authentification) à l'API Eurostat pour
rafraîchir la comparaison européenne (table demo_mlexpec).
"""

from io import StringIO

import numpy as np
import pandas as pd
import requests

HMD_BASE = "https://www.mortality.org/File/GetDocument/hmd.v6/FRACNP/STATS"

EUROSTAT_URL = (
    "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/demo_mlexpec"
)


def parse_hmd_text(text: str) -> pd.DataFrame | None:
    """Parse le contenu texte d'une table HMD 1x1 (fltper_1x1.txt / mltper_1x1.txt).

    Retourne un DataFrame avec colonnes : Year, Age, mx, qx, lx, dx, ex.
    """
    try:
        df = pd.read_csv(StringIO(text), sep=r"\s+", skiprows=2, na_values=".")
        df.columns = df.columns.str.strip()
        df["Age"] = pd.to_numeric(df["Age"].astype(str).str.replace("+", ""), errors="coerce")
        df = df.dropna(subset=["Age"])
        return df
    except Exception as e:
        print(f"HMD parse failed: {e}")
        return None


def download_hmd_table(sex: str, hmd_user: str, hmd_pwd: str) -> pd.DataFrame | None:
    """
    Télécharge et parse la table de mortalité période France (1x1).
    sex : 'f' pour femmes, 'm' pour hommes
    Retourne un DataFrame avec colonnes : Year, Age, mx, qx, lx, dx, ex
    """
    filename = "fltper_1x1.txt" if sex == "f" else "mltper_1x1.txt"
    url = f"{HMD_BASE}/{filename}"
    try:
        r = requests.get(url, auth=(hmd_user, hmd_pwd), timeout=15)
        r.raise_for_status()
        return parse_hmd_text(r.text)
    except Exception as e:
        print(f"HMD download failed: {e}")
        return None


def compute_percentiles_from_hmd(df: pd.DataFrame) -> pd.DataFrame:
    """
    Pour chaque année, calcule e0, Q1, médiane, Q3, IQR et écart-type
    à partir de la colonne dx (distribution des décès).
    """
    rows = []
    for year, grp in df.groupby("Year"):
        ages = grp["Age"].values
        dx = grp["dx"].values
        dx = np.maximum(dx, 0)
        total = dx.sum()
        if total == 0:
            continue
        weights = dx / total
        mean_age = np.average(ages, weights=weights)
        variance = np.average((ages - mean_age) ** 2, weights=weights)
        sd = np.sqrt(variance)
        cdf = np.cumsum(weights)
        q1 = ages[np.searchsorted(cdf, 0.25)]
        med = ages[np.searchsorted(cdf, 0.50)]
        q3 = ages[np.searchsorted(cdf, 0.75)]
        e0_col = grp["ex"].iloc[0] if "ex" in grp.columns else mean_age
        rows.append({"year": year, "e0": e0_col, "q1": q1, "median": med,
                     "q3": q3, "iqr": q3 - q1, "sd": sd, "mean_age": mean_age})
    return pd.DataFrame(rows)


def fetch_eurostat_life_expectancy(year: int = 2024) -> pd.DataFrame | None:
    """Interroge l'API Eurostat (format JSON-stat) pour l'espérance de vie
    à la naissance par pays et par sexe, pour une année donnée.

    Retourne un DataFrame avec colonnes : geo, e0_f, e0_m, e0_total — ou None
    si l'API est injoignable.
    """
    params = {
        "format": "JSON",
        "lang": "FR",
        "age": "Y_LT1",
        "sex": ["F", "M", "T"],
        "time": str(year),
    }
    try:
        r = requests.get(EUROSTAT_URL, params=params, timeout=20)
        r.raise_for_status()
        js = r.json()
        ids = js["id"]
        sizes = js["size"]
        dims = js["dimension"]
        # position -> code, pour chaque dimension
        cats = {
            d: {pos: code for code, pos in dims[d]["category"]["index"].items()}
            for d in ids
        }
        # strides pour décoder l'index linéaire JSON-stat
        strides = [1] * len(sizes)
        for i in range(len(sizes) - 2, -1, -1):
            strides[i] = strides[i + 1] * sizes[i + 1]
        rows = []
        for key, value in js["value"].items():
            idx = int(key)
            rec = {
                d: cats[d][(idx // strides[i]) % sizes[i]]
                for i, d in enumerate(ids)
            }
            rows.append({"geo": rec["geo"], "sex": rec["sex"], "value": value})
        if not rows:
            return None
        df = pd.DataFrame(rows)
        pivot = df.pivot_table(index="geo", columns="sex", values="value").reset_index()
        return pivot.rename(columns={"F": "e0_f", "M": "e0_m", "T": "e0_total"})
    except Exception as e:
        print(f"Eurostat fetch failed: {e}")
        return None


def eurostat_to_embedded_format(df: pd.DataFrame) -> list[dict]:
    """Convertit le résultat de l'API Eurostat au format de
    EU_LIFE_EXPECTANCY_2024 (noms français, codes à deux lettres).
    Ne conserve que les pays présents dans les données embarquées.
    """
    from data.european import EU_LIFE_EXPECTANCY_2024

    code_map = {"EL": "GR", "EU27_2020": "EU"}
    names = {row["code"]: row["country"] for row in EU_LIFE_EXPECTANCY_2024}
    out = []
    for _, r in df.iterrows():
        code = code_map.get(r["geo"], r["geo"])
        if code in names and pd.notna(r.get("e0_total")):
            out.append({
                "country": names[code],
                "code": code,
                "e0_f": float(r["e0_f"]) if pd.notna(r.get("e0_f")) else None,
                "e0_m": float(r["e0_m"]) if pd.notna(r.get("e0_m")) else None,
                "e0_total": float(r["e0_total"]),
            })
    return out
