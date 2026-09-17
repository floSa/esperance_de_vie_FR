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
