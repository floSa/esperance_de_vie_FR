"""Accès aux données du projet, lues depuis `data/sources/`.

Ces fichiers sont produits par `scripts/refresh_data.py` ; leur provenance
complète (URL, paramètres, millésime, date d'extraction) est dans
`data/sources/manifest.json`.

Reste dans `embedded.py` ce qu'aucune source ouverte ne publie : les tables de
survie *par génération* et l'espérance résiduelle détaillée par âge.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import pandas as pd

SOURCES_DIR = Path(__file__).resolve().parent / "sources"
MANIFEST = SOURCES_DIR / "manifest.json"

# Première année où les quartiles proviennent d'une table de mortalité réelle
# (Eurostat) et non des estimations historiques embarquées.
PREMIERE_ANNEE_MESUREE = 2014


class DonneesManquantes(FileNotFoundError):
    """Les fichiers de `data/sources/` n'ont pas été générés."""


def _read(nom: str) -> pd.DataFrame:
    path = SOURCES_DIR / f"{nom}.csv"
    if not path.exists():
        raise DonneesManquantes(
            f"{path.name} absent. Lancez : uv run python -m scripts.refresh_data"
        )
    return pd.read_csv(path)


@lru_cache(maxsize=1)
def manifest() -> dict:
    if not MANIFEST.exists():
        return {}
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def millesime(nom: str) -> str:
    """Résumé lisible de la provenance d'un jeu, pour l'afficher sous un graphique."""
    entry = manifest().get(nom, {})
    fournisseur = entry.get("fournisseur", "?")
    annees = entry.get("annees") or entry.get("annee_retenue", "?")
    extrait = str(entry.get("extrait_le", ""))[:10]
    return f"{fournisseur} · {annees} · extrait le {extrait}" if extrait else fournisseur


# ---------------------------------------------------------------------------
# Espérance de vie
# ---------------------------------------------------------------------------

AGES_INSEE = (0, 1, 20, 40, 60)


@lru_cache(maxsize=1)
def esperance_vie() -> pd.DataFrame:
    """Espérance de vie par année, sexe et âge exact, de 0 à 95 ans.

    Deux sources se complètent, distinguées par la colonne `source` :
    l'INSEE remonte à 1946 mais ne publie que cinq âges ; Eurostat publie les
    96 âges mais seulement depuis 1998. Sur les cinq âges communs, l'INSEE est
    prioritaire pour sa profondeur historique.
    """
    insee = _read("esperance_vie_fr_insee").assign(source="insee")
    eurostat = _read("esperance_vie_fr_tous_ages_eurostat").assign(source="eurostat")
    fusion = pd.concat([insee, eurostat], ignore_index=True)
    return fusion.sort_values(["sexe", "age", "year", "source"]).reset_index(drop=True)


@lru_cache(maxsize=1)
def ages_disponibles() -> tuple[int, ...]:
    return tuple(sorted(esperance_vie()["age"].unique().tolist()))


def source_de_l_age(age: int) -> str:
    """Nom du jeu de données d'où provient cet âge, pour afficher sa provenance."""
    return ("esperance_vie_fr_insee" if age in AGES_INSEE
            else "esperance_vie_fr_tous_ages_eurostat")


@lru_cache(maxsize=1)
def esperance_vie_longue() -> pd.DataFrame:
    """Espérance de vie à la naissance, tous sexes confondus, 1816–2023.

    Seule série couvrant l'avant-1946 : c'est elle qui porte les creux de 1918
    (grippe espagnole et guerre) et de 1940.
    """
    return _read("esperance_vie_fr_longue_owid")


def serie_par_sexe(age: int, source: str | None = None) -> pd.DataFrame:
    """Table large `year × sexe` pour un âge donné.

    `source` restreint à un fournisseur (`"insee"` ou `"eurostat"`). C'est ce
    qui permet de tracer tous les âges sur une période identique : Eurostat
    couvre les 96 âges sur la même fenêtre, l'INSEE seulement cinq d'entre eux
    mais depuis 1946.
    """
    df = esperance_vie()
    df = df[df["age"] == age]
    if source is not None:
        df = df[df["source"] == source]
    else:
        # Les deux sources se recouvrent sur cinq âges ; l'INSEE l'emporte pour
        # sa profondeur historique, sinon le pivot verrait deux valeurs par an.
        df = df.drop_duplicates(subset=["year", "sexe"], keep="first")
    return (df.pivot(index="year", columns="sexe", values="esperance")
              .dropna(how="all")
              .reset_index())


@lru_cache(maxsize=1)
def periode_comparable() -> tuple[int, int]:
    """Fenêtre d'années disponible pour **tous** les âges, sans exception."""
    euro = _read("esperance_vie_fr_tous_ages_eurostat")
    return int(euro["year"].min()), int(euro["year"].max())


# ---------------------------------------------------------------------------
# Distribution des âges au décès
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def distribution_deces() -> pd.DataFrame:
    """Quartiles des âges au décès, par année et par sexe.

    Deux régimes cohabitent et sont distingués par la colonne `mesure` :
    les années récentes sont calculées sur la distribution `dx` réelle de la
    table de mortalité Eurostat ; les années antérieures restent des
    estimations historiques, faute de source ouverte remontant avant 2014.
    """
    from data.embedded import PERIOD_DISTRIBUTION_FEMMES, PERIOD_DISTRIBUTION_HOMMES

    historique = pd.concat([
        pd.DataFrame(PERIOD_DISTRIBUTION_FEMMES).assign(sexe="femmes"),
        pd.DataFrame(PERIOD_DISTRIBUTION_HOMMES).assign(sexe="hommes"),
    ], ignore_index=True)
    historique = historique[historique["year"] < PREMIERE_ANNEE_MESUREE]
    historique["mesure"] = "estimée"

    mesure = _read("distribution_deces_eurostat").assign(mesure="mesurée")

    # L'espérance de vie des années mesurées vient de la série INSEE, pas des
    # estimations : les deux doivent raconter la même histoire.
    e0 = esperance_vie()
    e0 = e0[e0["age"] == 0][["year", "sexe", "esperance"]].rename(
        columns={"esperance": "e0"})
    mesure = mesure.merge(e0, on=["year", "sexe"], how="left")

    colonnes = ["year", "sexe", "e0", "q1", "median", "q3", "iqr", "mesure"]
    for col in ("sd", "mean_age"):
        if col in mesure.columns:
            colonnes.append(col)
            historique[col] = pd.NA

    return (pd.concat([historique[colonnes], mesure[colonnes]], ignore_index=True)
              .sort_values(["sexe", "year"])
              .reset_index(drop=True))


# ---------------------------------------------------------------------------
# Naissances et comparaison européenne
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def naissances() -> pd.Series:
    """Naissances vivantes annuelles, indexées par année (1901–2025)."""
    return _read("naissances_fr_insee").set_index("year")["naissances"]


@lru_cache(maxsize=1)
def europe() -> pd.DataFrame:
    """Espérance de vie à la naissance dans les 27 États membres.

    Le fichier source contient aussi des agrégats (zone euro, AELE) et des
    pays hors UE ; seuls les 27 et la moyenne UE sont retenus ici.
    """
    from data.european import PAYS_UE27

    df = _read("esperance_vie_europe_eurostat").rename(columns={"geo": "code"})
    df = df[df["code"].isin(PAYS_UE27)].copy()
    df["country"] = df["code"].map(PAYS_UE27)
    df["ecart_fh"] = df["e0_f"] - df["e0_m"]
    return df.sort_values("e0_total", ascending=False).reset_index(drop=True)


@lru_cache(maxsize=1)
def moyenne_ue() -> float | None:
    """Espérance de vie moyenne UE-27, telle que publiée par Eurostat."""
    from data.european import CODE_MOYENNE_UE

    df = _read("esperance_vie_europe_eurostat")
    ligne = df[df["geo"] == CODE_MOYENNE_UE]
    return float(ligne["e0_total"].iloc[0]) if len(ligne) else None


def annee_europe() -> int:
    return int(europe()["annee"].iloc[0])
