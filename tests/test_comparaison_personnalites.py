"""Règles de la comparaison personnalités / population.

Données synthétiques : ce qui est testé, c'est que les deux côtés sont
filtrés et agrégés de la même façon, pas les valeurs réelles.
"""

import pandas as pd
import pytest

from data import repository as repo


@pytest.fixture
def donnees(monkeypatch):
    population = pd.DataFrame([
        # 1990 : un enfant mort à 2 ans pèse lourd s'il n'est pas écarté.
        {"year": 1990, "sexe": "hommes", "age": 2, "deces": 1000},
        {"year": 1990, "sexe": "hommes", "age": 70, "deces": 100},
        {"year": 1990, "sexe": "hommes", "age": 80, "deces": 100},
        {"year": 1995, "sexe": "hommes", "age": 60, "deces": 300},
        {"year": 1995, "sexe": "hommes", "age": 90, "deces": 100},
        {"year": 2030, "sexe": "hommes", "age": 99, "deces": 5},
        {"year": 1990, "sexe": "femmes", "age": 85, "deces": 50},
    ])
    personnalites = pd.DataFrame([
        {"year": 1990, "sexe": "hommes", "age": 20},
        {"year": 1991, "sexe": "hommes", "age": 70},
        {"year": 1994, "sexe": "hommes", "age": 90},
        {"year": 1995, "sexe": "hommes", "age": 72},
        {"year": 1990, "sexe": "femmes", "age": 88},
    ])
    monkeypatch.setattr(repo, "deces_population", lambda: population)
    monkeypatch.setattr(repo, "personnalites", lambda: personnalites)


def test_meme_seuil_d_age_des_deux_cotes(donnees):
    periodes = repo.comparaison_age_deces("hommes").set_index("periode")
    # Population 1990–1994 : l'enfant de 2 ans est écarté → (70·100 + 80·100) / 200.
    assert periodes.loc[1990, "age_moyen_population"] == pytest.approx(75.0)
    # Personnalités 1990–1994 : le décès à 20 ans est écarté → (70 + 90) / 2.
    assert periodes.loc[1990, "age_moyen_personnalites"] == pytest.approx(80.0)
    assert periodes.loc[1990, "nb_personnalites"] == 2


def test_moyenne_population_ponderee_par_les_deces(donnees):
    periodes = repo.comparaison_age_deces("hommes").set_index("periode")
    # (60·300 + 90·100) / 400, et non la moyenne simple des âges (75).
    assert periodes.loc[1995, "age_moyen_population"] == pytest.approx(67.5)


def test_periode_limitee_aux_annees_communes(donnees):
    periodes = repo.comparaison_age_deces("hommes")
    # 2030 n'existe que côté population : il ne doit pas apparaître.
    assert periodes["periode"].max() == 1995
    assert periodes["libelle"].tolist() == ["1990–1994", "1995–1995"]


def test_sexes_separes(donnees):
    femmes = repo.comparaison_age_deces("femmes")
    assert len(femmes) == 1
    assert femmes["age_moyen_personnalites"].iloc[0] == pytest.approx(88.0)
    assert femmes["age_moyen_population"].iloc[0] == pytest.approx(85.0)


def test_bilan_coherent_avec_les_periodes(donnees):
    bilan = repo.bilan_age_deces("hommes")
    # Personnalités ≥ 25 ans sur 1990–1995 : 70, 90, 72.
    assert bilan["personnalites"] == pytest.approx((70 + 90 + 72) / 3)
    assert bilan["nb_personnalites"] == 3
    assert bilan["ecart"] == pytest.approx(bilan["personnalites"] - bilan["population"])


@pytest.fixture
def prediction(monkeypatch):
    esperance = pd.DataFrame([
        {"year": 1960, "sexe": "hommes", "age": 60, "esperance": 15.0, "source": "insee"},
        {"year": 1970, "sexe": "hommes", "age": 60, "esperance": 17.0, "source": "insee"},
        # Même année, autre source : ne doit pas être utilisée.
        {"year": 1960, "sexe": "hommes", "age": 60, "esperance": 99.0, "source": "eurostat"},
    ])
    personnalites = pd.DataFrame([
        {"year": 1995, "sexe": "hommes", "age": 95, "annee_naissance": 1900, "nom": "A"},
        {"year": 1990, "sexe": "hommes", "age": 70, "annee_naissance": 1910, "nom": "B"},
        {"year": 1992, "sexe": "hommes", "age": 45, "annee_naissance": 1947, "nom": "C"},
    ])
    population = pd.DataFrame([
        # Mort en 1990 à 90 ans → 60 ans en 1960 → âge prédit 75 → écart +15.
        {"year": 1990, "sexe": "hommes", "age": 90, "deces": 100},
        # Mort en 1990 à 80 ans → 60 ans en 1970 → âge prédit 77 → écart +3.
        {"year": 1990, "sexe": "hommes", "age": 80, "deces": 300},
        # Trop jeune pour une prédiction à 60 ans.
        {"year": 1990, "sexe": "hommes", "age": 50, "deces": 1000},
    ])
    monkeypatch.setattr(repo, "esperance_vie", lambda: esperance)
    monkeypatch.setattr(repo, "personnalites", lambda: personnalites)
    monkeypatch.setattr(repo, "deces_population", lambda: population)


def test_age_predit_pris_l_annee_des_60_ans(prediction):
    ecarts, avant_60 = repo.ecarts_personnalites("hommes", 1990, 1999)
    ecarts = ecarts.set_index("nom")
    # A : né en 1900, 60 ans en 1960 → 60 + 15 = 75, mort à 95 → +20.
    assert ecarts.loc["A", "age_predit"] == pytest.approx(75.0)
    assert ecarts.loc["A", "ecart"] == pytest.approx(20.0)
    # B : né en 1910, 60 ans en 1970 → 60 + 17 = 77, mort à 70 → −7.
    assert ecarts.loc["B", "ecart"] == pytest.approx(-7.0)
    # C, mort à 45 ans, n'a pas d'âge prédit : compté à part.
    assert "C" not in ecarts.index
    assert avant_60 == 1


def test_population_meme_calcul_pondere(prediction):
    pop = repo.ecarts_population("hommes", 1990, 1990)
    assert sorted(pop["ecart"].round(6)) == [3.0, 15.0]
    part, mediane = repo.part_apres_et_mediane(pop["ecart"], pop["deces"])
    assert part == pytest.approx(1.0)
    # 300 décès à +3 contre 100 à +15 : la médiane pondérée est +3.
    assert mediane == pytest.approx(3.0)


def test_part_apres_exclut_l_ecart_nul():
    ecarts = pd.Series([-2.0, 0.0, 1.0, 4.0])
    part, mediane = repo.part_apres_et_mediane(ecarts)
    assert part == pytest.approx(0.5)
    assert mediane == pytest.approx(0.0)


@pytest.fixture
def nuage(monkeypatch):
    esperance = pd.DataFrame([
        {"year": 1990, "sexe": "hommes", "age": 60, "esperance": 20.0, "source": "insee"},
    ])
    personnalites = pd.DataFrame([
        # Même naissance, même année de décès : un seul point.
        {"year": 2010, "sexe": "hommes", "age": 80, "annee_naissance": 1930,
         "nom": "Très connu", "nb_editions_wikipedia": 90, "wikidata_id": "Q1"},
        {"year": 2010, "sexe": "hommes", "age": 79, "annee_naissance": 1930,
         "nom": "Peu connu", "nb_editions_wikipedia": 2, "wikidata_id": "Q2"},
        {"year": 2031, "sexe": "hommes", "age": 101, "annee_naissance": 1930,
         "nom": "Centenaire", "nb_editions_wikipedia": 5, "wikidata_id": "Q3"},
    ])
    population = pd.DataFrame([
        {"year": 2010, "sexe": "hommes", "age": 80, "deces": 10},
        {"year": 2030, "sexe": "hommes", "age": 100, "deces": 999},  # classe ouverte
    ])
    monkeypatch.setattr(repo, "esperance_vie", lambda: esperance)
    monkeypatch.setattr(repo, "personnalites", lambda: personnalites)
    monkeypatch.setattr(repo, "deces_population", lambda: population)
    monkeypatch.setattr(repo, "MIN_PERSONNALITES_PAR_NAISSANCE", 1)


def test_un_point_par_naissance_et_deces(nuage):
    points = repo.points_personnalites("hommes", 2000, 2040)
    groupe = points[(points["annee_naissance"] == 1930) & (points["year"] == 2010)].iloc[0]
    assert groupe["nb"] == 2
    # Les plus connues d'abord, écart formaté à la française.
    assert groupe["noms"].startswith("Très connu — 80 ans (+0,0)")
    assert len(points) == 2


def test_courbes_par_naissance_sans_classe_ouverte(nuage):
    pop = repo.age_moyen_population_par_naissance("hommes", 2000, 2040)
    # La classe « 100 ans et plus » n'a ni âge ni naissance exacts : écartée.
    assert pop["annee_naissance"].tolist() == [1930]
    assert pop["age_moyen"].iloc[0] == pytest.approx(80.0)
    pers = repo.age_moyen_personnalites_par_naissance("hommes", 2000, 2040)
    # Même règle côté personnalités : le centenaire ne compte pas.
    assert pers["age_moyen"].iloc[0] == pytest.approx(79.5)
    assert pers["nb"].iloc[0] == 2
