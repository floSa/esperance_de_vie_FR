"""Comparaison européenne de l'espérance de vie.

Source : Eurostat, table demo_mlexpec, 2024.
À compléter avec l'API Eurostat si besoin (voir loader.py).
"""

EU_LIFE_EXPECTANCY_2024 = [
    {"country": "Espagne",      "code": "ES", "e0_f": 86.5, "e0_m": 80.8, "e0_total": 83.7},
    {"country": "Suède",        "code": "SE", "e0_f": 84.7, "e0_m": 82.6, "e0_total": 83.7},
    {"country": "Italie",       "code": "IT", "e0_f": 85.1, "e0_m": 81.4, "e0_total": 83.3},
    {"country": "Chypre",       "code": "CY", "e0_f": 84.5, "e0_m": 80.5, "e0_total": 82.5},
    {"country": "Luxembourg",   "code": "LU", "e0_f": 84.9, "e0_m": 80.3, "e0_total": 82.6},
    {"country": "France",       "code": "FR", "e0_f": 85.8, "e0_m": 80.2, "e0_total": 83.0},
    {"country": "Irlande",      "code": "IE", "e0_f": 84.1, "e0_m": 81.0, "e0_total": 82.6},
    {"country": "Autriche",     "code": "AT", "e0_f": 83.5, "e0_m": 79.4, "e0_total": 81.5},
    {"country": "Pays-Bas",     "code": "NL", "e0_f": 83.7, "e0_m": 80.9, "e0_total": 82.3},
    {"country": "Finlande",     "code": "FI", "e0_f": 83.5, "e0_m": 78.7, "e0_total": 81.1},
    {"country": "Belgique",     "code": "BE", "e0_f": 83.5, "e0_m": 79.6, "e0_total": 81.6},
    {"country": "Allemagne",    "code": "DE", "e0_f": 82.9, "e0_m": 78.7, "e0_total": 80.8},
    {"country": "Grèce",        "code": "GR", "e0_f": 82.7, "e0_m": 78.1, "e0_total": 80.4},
    {"country": "Portugal",     "code": "PT", "e0_f": 83.6, "e0_m": 77.7, "e0_total": 80.7},
    {"country": "Danemark",     "code": "DK", "e0_f": 82.8, "e0_m": 79.4, "e0_total": 81.1},
    {"country": "Slovénie",     "code": "SI", "e0_f": 83.6, "e0_m": 78.4, "e0_total": 81.0},
    {"country": "Pologne",      "code": "PL", "e0_f": 80.9, "e0_m": 73.9, "e0_total": 77.4},
    {"country": "Tchéquie",     "code": "CZ", "e0_f": 81.3, "e0_m": 76.2, "e0_total": 78.8},
    {"country": "Croatie",      "code": "HR", "e0_f": 80.7, "e0_m": 74.8, "e0_total": 77.8},
    {"country": "Estonie",      "code": "EE", "e0_f": 81.6, "e0_m": 73.2, "e0_total": 77.4},
    {"country": "Lituanie",     "code": "LT", "e0_f": 80.9, "e0_m": 72.3, "e0_total": 76.6},
    {"country": "Lettonie",     "code": "LV", "e0_f": 79.7, "e0_m": 69.9, "e0_total": 74.8},
    {"country": "Hongrie",      "code": "HU", "e0_f": 79.2, "e0_m": 73.4, "e0_total": 76.3},
    {"country": "Slovaquie",    "code": "SK", "e0_f": 79.8, "e0_m": 73.6, "e0_total": 76.7},
    {"country": "Roumanie",     "code": "RO", "e0_f": 78.9, "e0_m": 72.5, "e0_total": 75.7},
    {"country": "Bulgarie",     "code": "BG", "e0_f": 77.5, "e0_m": 71.2, "e0_total": 74.4},
    {"country": "Moy. UE-27",   "code": "EU", "e0_f": 84.1, "e0_m": 78.9, "e0_total": 81.5},
]
