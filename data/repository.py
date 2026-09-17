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


# ---------------------------------------------------------------------------
# Personnalités et population
# ---------------------------------------------------------------------------

# On devient rarement célèbre avant l'âge adulte. Compter les décès d'enfants
# dans la population, et pas chez les personnalités, abaisserait artificiellement
# l'âge moyen au décès de la population.
AGE_ADULTE = 25
DUREE_PERIODE = 5


@lru_cache(maxsize=1)
def deces_population() -> pd.DataFrame:
    """Décès enregistrés en France par année, sexe et âge (Eurostat)."""
    return _read("deces_par_age_eurostat")


@lru_cache(maxsize=1)
def personnalites() -> pd.DataFrame:
    """Personnalités françaises décédées, avec âge exact au décès (Wikidata)."""
    return _read("deces_personnalites_wikidata")


def _periode(annee: pd.Series, debut: int) -> pd.Series:
    return debut + (annee - debut) // DUREE_PERIODE * DUREE_PERIODE


def comparaison_age_deces(sexe: str, age_min: int = AGE_ADULTE) -> pd.DataFrame:
    """Âge moyen au décès par période de 5 ans : personnalités contre population.

    Des deux côtés, la même population est comparée : les personnes mortes
    pendant la période, à `age_min` ans ou plus, du même sexe. Seules les années
    couvertes par les deux sources sont retenues.
    """
    pop = deces_population()
    pers = personnalites()
    debut, fin = annees_communes()

    pop = pop[(pop["sexe"] == sexe) & (pop["age"] >= age_min)
              & pop["year"].between(debut, fin)].copy()
    pers = pers[(pers["sexe"] == sexe) & (pers["age"] >= age_min)
                & pers["year"].between(debut, fin)].copy()
    pop["periode"] = _periode(pop["year"], debut)
    pers["periode"] = _periode(pers["year"], debut)

    pop["age_x_deces"] = pop["age"] * pop["deces"]
    cote_pop = pop.groupby("periode").agg(age_x=("age_x_deces", "sum"),
                                          deces=("deces", "sum"))
    cote_pop["age_moyen_population"] = cote_pop["age_x"] / cote_pop["deces"]
    cote_pers = pers.groupby("periode").agg(age_moyen_personnalites=("age", "mean"),
                                            nb_personnalites=("age", "size"))

    out = cote_pop[["age_moyen_population"]].join(cote_pers, how="inner").reset_index()
    out["fin_periode"] = (out["periode"] + DUREE_PERIODE - 1).clip(upper=fin)
    out["libelle"] = out["periode"].astype(str) + "–" + out["fin_periode"].astype(str)
    out["ecart"] = out["age_moyen_personnalites"] - out["age_moyen_population"]
    return out


def bilan_age_deces(sexe: str, age_min: int = AGE_ADULTE) -> dict:
    """Moyennes sur toute la période commune aux deux sources."""
    pop, pers = deces_population(), personnalites()
    debut, fin = annees_communes()
    pop = pop[(pop["sexe"] == sexe) & (pop["age"] >= age_min) & pop["year"].between(debut, fin)]
    pers = pers[(pers["sexe"] == sexe) & (pers["age"] >= age_min)
                & pers["year"].between(debut, fin)]
    moy_pop = float((pop["age"] * pop["deces"]).sum() / pop["deces"].sum())
    moy_pers = float(pers["age"].mean())
    return {"debut": debut, "fin": fin, "population": moy_pop,
            "personnalites": moy_pers, "ecart": moy_pers - moy_pop,
            "nb_personnalites": len(pers)}


# ---------------------------------------------------------------------------
# Personnalités : écart à l'âge de décès prédit
# ---------------------------------------------------------------------------

# L'âge prédit se calcule à 60 ans et non à la naissance : l'INSEE ne publie
# l'espérance de vie qu'à partir de 1946, et celle à la naissance compte les
# décès d'enfants, auxquels toute personnalité a par définition survécu.
AGE_PREDICTION = 60


def annees_communes() -> tuple[int, int]:
    """Années couvertes à la fois par les décès Eurostat et par les personnalités."""
    pop, pers = deces_population(), personnalites()
    return (max(int(pop["year"].min()), int(pers["year"].min())),
            min(int(pop["year"].max()), int(pers["year"].max())))


def periodes_communes() -> list[tuple[int, int, str]]:
    debut, fin = annees_communes()
    return [(a, min(a + DUREE_PERIODE - 1, fin), f"{a}–{min(a + DUREE_PERIODE - 1, fin)}")
            for a in range(debut, fin + 1, DUREE_PERIODE)]


def _esperance_a_60() -> pd.DataFrame:
    e = esperance_vie()
    e = e[(e["age"] == AGE_PREDICTION) & (e["source"] == "insee")]
    return e.rename(columns={"year": "annee_60", "esperance": "e60"})[["annee_60", "sexe", "e60"]]


def ecarts_personnalites(sexe: str, debut: int, fin: int) -> tuple[pd.DataFrame, int]:
    """Âge au décès face à l'âge prédit, personnalité par personnalité.

    Âge prédit = 60 + espérance de vie à 60 ans, l'année où la personne a eu
    60 ans, pour son sexe. Renvoie aussi le nombre de personnalités mortes avant
    60 ans, qui n'ont pas d'âge prédit.
    """
    pers = personnalites()
    pers = pers[(pers["sexe"] == sexe) & pers["year"].between(debut, fin)]
    avant_60 = int((pers["age"] < AGE_PREDICTION).sum())
    pers = pers[pers["age"] >= AGE_PREDICTION].assign(
        annee_60=lambda d: d["annee_naissance"] + AGE_PREDICTION)
    out = pers.merge(_esperance_a_60(), on=["annee_60", "sexe"], how="inner")
    out["age_predit"] = AGE_PREDICTION + out["e60"]
    out["ecart"] = out["age"] - out["age_predit"]
    return out.reset_index(drop=True), avant_60


def ecarts_population(sexe: str, debut: int, fin: int) -> pd.DataFrame:
    """Même calcul sur tous les décès enregistrés, pondéré par le nombre de décès.

    L'année des 60 ans se déduit de l'année et de l'âge au décès. Le groupe
    « 100 ans et plus » est gardé à 100 ans : son écart est sous-estimé, mais
    il est de toute façon positif.
    """
    pop = deces_population()
    pop = pop[(pop["sexe"] == sexe) & pop["year"].between(debut, fin)
              & (pop["age"] >= AGE_PREDICTION)]
    pop = pop.assign(annee_60=pop["year"] - pop["age"] + AGE_PREDICTION)
    out = pop.merge(_esperance_a_60(), on=["annee_60", "sexe"], how="inner")
    out["ecart"] = out["age"] - (AGE_PREDICTION + out["e60"])
    return out.reset_index(drop=True)


def part_apres_et_mediane(ecarts: pd.Series, poids: pd.Series | None = None) -> tuple[float, float]:
    """Part des décès survenus après l'âge prédit, et écart médian."""
    if poids is None:
        poids = pd.Series(1, index=ecarts.index)
    total = float(poids.sum())
    part = float(poids[ecarts > 0].sum()) / total
    ordre = ecarts.sort_values()
    cumul = poids.loc[ordre.index].cumsum() / total
    mediane = float(ordre[cumul >= 0.5].iloc[0])
    return part, mediane


def points_personnalites(sexe: str, debut: int, fin: int, noms_max: int = 6) -> pd.DataFrame:
    """Un point par couple (année de naissance, année de décès).

    Les personnalités nées la même année et mortes la même année partagent un
    point. Le libellé liste les plus connues d'entre elles avec leur écart.
    """
    ecarts, _ = ecarts_personnalites(sexe, debut, fin)
    ecarts = ecarts.sort_values("nb_editions_wikipedia", ascending=False)

    def libelle(groupe: pd.DataFrame) -> str:
        lignes = [f"{r.nom} — {r.age} ans ({f'{r.ecart:+.1f}'.replace('.', ',')})"
                  for r in groupe.head(noms_max).itertuples()]
        if len(groupe) > noms_max:
            lignes.append(f"… et {len(groupe) - noms_max} autres")
        return "<br>".join(lignes)

    groupes = ecarts.groupby(["annee_naissance", "year"], sort=False)
    points = groupes.agg(nb=("nom", "size"), age=("age", "mean"),
                         age_predit=("age_predit", "mean"),
                         ecart=("ecart", "mean")).reset_index()
    points["noms"] = groupes.apply(libelle, include_groups=False).to_numpy()
    return points


# Eurostat regroupe les décès de 100 ans et plus dans une classe ouverte : ni
# l'âge exact ni l'année de naissance n'y sont connus. Les courbes par année de
# naissance s'arrêtent donc à 99 ans, des deux côtés.
AGE_CLASSE_OUVERTE = 100


def age_moyen_population_par_naissance(sexe: str, debut: int, fin: int) -> pd.DataFrame:
    """Âge moyen au décès des Français nés une année donnée, morts entre `debut` et `fin`.

    Référence soumise au même effet de fenêtre que les personnalités : une
    génération ancienne n'apparaît que par ceux encore vivants en `debut`, une
    génération récente que par ceux déjà morts en `fin`.
    """
    pop = deces_population()
    pop = pop[(pop["sexe"] == sexe) & pop["year"].between(debut, fin)
              & pop["age"].between(AGE_PREDICTION, AGE_CLASSE_OUVERTE - 1)]
    pop = pop.assign(annee_naissance=pop["year"] - pop["age"],
                     age_x_deces=pop["age"] * pop["deces"])
    out = pop.groupby("annee_naissance").agg(age_x=("age_x_deces", "sum"),
                                             deces=("deces", "sum")).reset_index()
    out["age_moyen"] = out["age_x"] / out["deces"]
    return out[["annee_naissance", "age_moyen", "deces"]]


def age_predit_par_naissance(sexe: str) -> pd.DataFrame:
    e = _esperance_a_60()
    e = e[e["sexe"] == sexe]
    return pd.DataFrame({"annee_naissance": e["annee_60"] - AGE_PREDICTION,
                         "age_predit": AGE_PREDICTION + e["e60"]}).sort_values("annee_naissance")


# En dessous, la moyenne d'une année de naissance repose sur trop peu de
# personnalités pour être tracée sans zigzags trompeurs.
MIN_PERSONNALITES_PAR_NAISSANCE = 10


def age_moyen_personnalites_par_naissance(sexe: str, debut: int, fin: int) -> pd.DataFrame:
    """Âge moyen au décès des personnalités, par année de naissance.

    Même fenêtre d'observation que `age_moyen_population_par_naissance` : les
    deux courbes se comparent directement.
    """
    ecarts, _ = ecarts_personnalites(sexe, debut, fin)
    ecarts = ecarts[ecarts["age"] < AGE_CLASSE_OUVERTE]
    out = ecarts.groupby("annee_naissance").agg(age_moyen=("age", "mean"),
                                                nb=("age", "size")).reset_index()
    return out[out["nb"] >= MIN_PERSONNALITES_PAR_NAISSANCE]
