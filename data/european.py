"""Nomenclature des pays européens : codes Eurostat → noms français.

Référentiel, pas des mesures : les valeurs d'espérance de vie viennent de
`data/sources/esperance_vie_europe_eurostat.csv`, régénéré par
`scripts/refresh_data.py`.
"""

# Les 27 États membres. Eurostat code la Grèce « EL » et non « GR ».
PAYS_UE27 = {
    "AT": "Autriche",
    "BE": "Belgique",
    "BG": "Bulgarie",
    "CY": "Chypre",
    "CZ": "Tchéquie",
    "DE": "Allemagne",
    "DK": "Danemark",
    "EE": "Estonie",
    "EL": "Grèce",
    "ES": "Espagne",
    "FI": "Finlande",
    "FR": "France",
    "HR": "Croatie",
    "HU": "Hongrie",
    "IE": "Irlande",
    "IT": "Italie",
    "LT": "Lituanie",
    "LU": "Luxembourg",
    "LV": "Lettonie",
    "MT": "Malte",
    "NL": "Pays-Bas",
    "PL": "Pologne",
    "PT": "Portugal",
    "RO": "Roumanie",
    "SE": "Suède",
    "SI": "Slovénie",
    "SK": "Slovaquie",
}

CODE_MOYENNE_UE = "EU27_2020"
