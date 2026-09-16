"""Invariants démographiques de la survie par génération.

Ces propriétés ne dépendent d'aucune valeur chiffrée précise : elles doivent
tenir quelles que soient les ancres retenues. C'est ce qui en fait un filet
utile quand on retouche l'interpolation.
"""

import pytest

from common import age_max_documente, get_cohort_survival, interp_survival
from data.embedded import COHORT_SURVIVAL

SEXES = ["femmes", "hommes"]
AGES = [0, 1, 10, 20, 35, 50, 60, 65, 70, 80]


@pytest.mark.parametrize("sexe", SEXES)
@pytest.mark.parametrize("annee", range(1930, 1991, 5))
def test_survie_decroit_avec_age(sexe, annee):
    """On ne ressuscite pas : la part de vivants ne peut que baisser avec l'âge."""
    precedent = 100.0
    for age in range(96):
        valeur = get_cohort_survival(sexe, annee, age)
        if valeur is None:
            break
        assert valeur <= precedent + 1e-9, (
            f"{sexe} nés en {annee} : remontée de {precedent:.2f} % à "
            f"{valeur:.2f} % entre {age - 1} et {age} ans"
        )
        precedent = valeur


@pytest.mark.parametrize("sexe", SEXES)
@pytest.mark.parametrize("age", AGES)
def test_survie_progresse_entre_generations(sexe, age):
    """À âge égal, une génération plus récente survit au moins aussi bien.

    C'est l'invariant qui manquait : l'ancienne extrapolation faisait chuter la
    survie à 65 ans de 85 % (génération 1960) à 79,5 % (1965) avant de remonter
    à 89,5 % (1970).

    La tolérance de 0,5 point absorbe l'arrondi des ancres embarquées (données
    déclarées à ±5 %) tout en restant dix fois plus fine que le défaut qu'il
    s'agit d'empêcher.
    """
    precedent = None
    for annee in range(1930, 1991):
        valeur = get_cohort_survival(sexe, annee, age)
        if valeur is None:
            continue
        if precedent is not None:
            annee_prec, pct_prec = precedent
            assert valeur >= pct_prec - 0.5, (
                f"{sexe} à {age} ans : la génération {annee} survit moins "
                f"({valeur:.1f} %) que la génération {annee_prec} "
                f"({pct_prec:.1f} %)"
            )
        precedent = (annee, valeur)


@pytest.mark.parametrize("sexe", SEXES)
@pytest.mark.parametrize("annee", range(1930, 1991, 10))
@pytest.mark.parametrize("age", AGES)
def test_pourcentage_dans_les_bornes(sexe, annee, age):
    valeur = get_cohort_survival(sexe, annee, age)
    assert valeur is None or 0.0 <= valeur <= 100.0


@pytest.mark.parametrize("sexe", SEXES)
def test_pas_extrapolation_au_dela_des_donnees(sexe):
    """Aucune génération ne se voit attribuer une survie à un âge non atteint."""
    age_max_connu = max(ancres[-1][0] for ancres in COHORT_SURVIVAL[sexe].values())
    assert get_cohort_survival(sexe, 1960, age_max_connu + 5) is None


@pytest.mark.parametrize("sexe", SEXES)
def test_age_max_documente_donne_toujours_une_valeur(sexe):
    """Borne exploitable par les pages, pour toutes les générations du curseur.

    La génération 1930 a dépassé 95 ans : demander sa survie à son âge réel
    renvoyait `None`, et l'explorateur de cohorte plantait sur une
    multiplication par `None`.
    """
    borne = age_max_documente(sexe)
    for annee in range(1930, 1991):
        assert get_cohort_survival(sexe, annee, borne) is not None, (
            f"{sexe} nés en {annee} : aucune valeur à {borne} ans"
        )
    assert get_cohort_survival(sexe, 1930, borne + 1) is None


@pytest.mark.parametrize("sexe", SEXES)
def test_naissance_a_cent_pour_cent(sexe):
    for annee in (1930, 1960, 1990):
        assert get_cohort_survival(sexe, annee, 0) == pytest.approx(100.0)


def test_interp_survival_borne_superieure():
    ancres = [(0, 100.0), (50, 90.0), (60, 80.0)]
    assert interp_survival(ancres, 55) == pytest.approx(85.0)
    assert interp_survival(ancres, 60) == pytest.approx(80.0)
    assert interp_survival(ancres, 61) is None


def test_les_femmes_survivent_mieux_que_les_hommes():
    """Écart de mortalité par sexe, constant sur toute la période française."""
    for annee in (1930, 1950, 1970):
        for age in (60, 65, 70):
            f = get_cohort_survival("femmes", annee, age)
            h = get_cohort_survival("hommes", annee, age)
            if f is not None and h is not None:
                assert f > h, f"génération {annee} à {age} ans : {f} vs {h}"
