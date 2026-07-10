# 📊 Espérance de vie — France & Europe

Application **Streamlit** multi-pages analysant l'espérance de vie en France
(1900–2025) et en Europe, construite à partir des tables de mortalité
**HMD** (Human Mortality Database, mortality.org), de l'**INSEE**
(Vallin & Meslé) et d'**Eurostat** (table `demo_mlexpec`).

Une partie des données est **embarquée** (approximations démographiques
validées), une partie peut être **rafraîchie via API** (Eurostat sans
authentification, HMD avec credentials).

## Lancement

Le projet est géré avec [uv](https://docs.astral.sh/uv/) (Python 3.12) :

```bash
uv sync
uv run streamlit run app.py
```

## Les quatre vues

| Page | Contenu |
|---|---|
| 📈 **Vue générale** | Évolution de e₀ / e₆₀ / e₆₅ (1900–2025), annotations WWI/WWII/Covid, comparaison des 26 pays UE (barres triées, moyenne UE-27), tops 10 |
| 📐 **Distribution & variance** | Bande Q1–Q3 des âges au décès, médiane vs e₀, évolution de l'IQR (67 ans → 13 ans) : la **compression de la mortalité** |
| 👥 **Explorateur de cohorte** | Pour une année de naissance (1930–1990) et un sexe : courbe de survie interpolée, effectifs nés / vivants / décédés, espérance résiduelle 2025 |
| 🔄 **Âge fixe × générations** | À âge constant (35–90 ans), % de la génération encore en vie selon l'année d'observation — comparaison entre cohortes |

## Structure

```
├── app.py                        # point d'entrée Streamlit
├── common.py                     # palette, template Plotly, interpolation cohortes
├── pages/
│   ├── 01_vue_generale.py
│   ├── 02_distribution_variance.py
│   ├── 03_cohorte_explorer.py
│   └── 04_age_fixe_generations.py
└── data/
    ├── loader.py                 # téléchargement HMD + API Eurostat
    ├── embedded.py               # données approx. (quartiles, cohortes, naissances)
    └── european.py               # comparaison européenne Eurostat 2024
```

## Données HMD complètes (optionnel)

L'inscription gratuite sur [mortality.org](https://www.mortality.org) permet de
recalculer les vrais quartiles et l'écart-type depuis les tables 1x1 :

```bash
export HMD_USER="votre@email.com"
export HMD_PASSWORD="motdepasse"
uv run streamlit run app.py
```

ou en important directement `fltper_1x1.txt` / `mltper_1x1.txt` sur la page
**Distribution & variance**.

## Lint

```bash
uv run ruff check .
```

## Sources

- HMD — Human Mortality Database, [mortality.org](https://www.mortality.org)
- INSEE — tables de mortalité françaises (Vallin & Meslé), naissances France métropolitaine
- Eurostat — table `demo_mlexpec` (2024)
- DREES 2024 — espérance de vie résiduelle
- Wilmoth & Horiuchi (1999), Robine (2001) — compression de la mortalité

*Estimations approximatives : survie de cohorte estimée à ±5 %.*
