# Documentation technique — Espérance de vie · France & Europe

Documentation méthodologique de l'application Streamlit d'analyse de l'espérance
de vie. Elle détaille le **problème étudié**, les **données**, les **méthodes de
calcul** (avec formules), les **hypothèses**, les **résultats chiffrés** et,
surtout, les **limites de représentativité** des estimations affichées.

> Vue d'ensemble et démarrage : [README.md](README.md).

---

## 1. Problème étudié

L'application ne prédit rien : elle **décrit et met en scène** l'évolution de la
mortalité française sur **1900–2025** et la compare au reste de l'Europe. Quatre
questions structurent les quatre pages :

| Page | Question posée | Indicateur central |
|---|---|---|
| Vue générale | Comment évolue l'espérance de vie et où se situe la France en Europe ? | e₀, e₆₀, e₆₅ |
| Distribution & variance | Les âges au décès se sont-ils resserrés autour d'un âge élevé ? | Quartiles Q1–Q3, IQR, écart-type |
| Explorateur de cohorte | Parmi les personnes nées une année donnée, combien sont encore en vie ? | Courbe de survie, effectifs |
| Âge fixe × générations | À âge constant, la survie s'améliore-t-elle d'une génération à l'autre ? | % vivants à âge fixe |

**Vocabulaire démographique manipulé** :

| Terme | Sens |
|---|---|
| `e₀` | Espérance de vie **à la naissance** (années) |
| `e₆₀`, `e₆₅` | Espérance de vie **résiduelle** à 60 / 65 ans |
| Table **du moment** (période) | Mortalité observée une année donnée, appliquée à tous les âges — une génération *fictive* |
| Table de **génération** (cohorte) | Mortalité réellement subie par les personnes nées la même année |
| `dx` | Distribution des décès par âge dans une table de mortalité (colonne HMD) |
| IQR | Écart interquartile `Q3 − Q1` : fenêtre d'âge contenant **50 %** des décès |

**Difficulté spécifique** : distinguer la logique **période** de la logique
**génération**. Une table du moment (ex. 2025) mesure les conditions de mortalité
d'une année ; elle ne décrit **aucune personne réelle** de bout en bout. Une table
de génération suit une cohorte, mais reste incomplète tant que la cohorte n'est pas
éteinte. L'app manipule les deux et l'affiche explicitement.

---

## 2. Données & provenance

| Source | Contenu utilisé | Accès |
|---|---|---|
| **HMD** — Human Mortality Database ([mortality.org](https://www.mortality.org)) | Tables de mortalité période France 1x1 (`fltper_1x1.txt`, `mltper_1x1.txt`), colonnes `Year, Age, mx, qx, lx, dx, ex` | API avec credentials `HMD_USER` / `HMD_PASSWORD`, **ou** upload manuel |
| **INSEE** (Vallin & Meslé) | Séries longues e₀ / e₆₀ / e₆₅, tables de génération, naissances France métropolitaine | Embarqué (approximations) |
| **Eurostat** — table `demo_mlexpec` | e₀ par pays et sexe, 26 pays UE + moyenne UE-27, année 2024 | API publique **sans authentification** |
| **DREES 2024** | Espérance de vie résiduelle du moment 2025 | Embarqué (approximations) |

### 2.1 Deux régimes de données

- **Embarqué** (`data/embedded.py`, `data/european.py`) : approximations validées,
  servant de **repli** quand les credentials HMD sont absents. Toujours sourcées
  dans l'interface. Précision annoncée : **survie de cohorte à ±5 %**.
- **Rafraîchi via API** (`data/loader.py`) : tables HMD complètes (recalcul des
  vrais quartiles/écart-type) et comparaison Eurostat pour une année choisie.

> **Décision** — *Données embarquées comme socle par défaut* **plutôt que**
> dépendance systématique aux API, **parce que** HMD exige une inscription et des
> credentials : l'app doit rester utilisable hors-ligne et sans compte. **Limite** :
> les valeurs par défaut sont des approximations arrondies, pas les tables brutes.

### 2.2 Structures embarquées (`data/embedded.py`)

| Constante | Forme | Rôle |
|---|---|---|
| `PERIOD_DISTRIBUTION_FEMMES` / `_HOMMES` | liste `{year, e0, q1, median, q3, iqr}`, 1900→2025 par décennie | Distribution des âges au décès (période) |
| `E60_SERIES`, `E65_SERIES` | `{sexe: {année: valeur}}` | Espérance résiduelle à 60 / 65 ans |
| `COHORT_SURVIVAL` | `{sexe: {année_naissance: [(âge, % vivants), …]}}`, 1930→1990 | Ancres de survie par génération |
| `BIRTHS_BY_YEAR` | `{année: effectif}`, 1930→1990 | Naissances France métropolitaine |
| `SEX_RATIO` | `femmes 0,487 · hommes 0,513` | Répartition des naissances par sexe |
| `RESIDUAL_LIFE_2025` | `{sexe: {âge: années restantes}}` | Espérance résiduelle, table du moment 2025 |

---

## 3. Méthodes de calcul

### 3.1 Distribution des âges au décès (depuis `dx`) — `compute_percentiles_from_hmd`

Pour chaque année, à partir de la distribution des décès `dx` par âge :

- Poids normalisés : $w_x = \dfrac{d_x}{\sum_x d_x}$ (avec $d_x$ borné à $\geq 0$).
- Âge moyen au décès : $\bar{a} = \sum_x w_x \, x$.
- Variance / écart-type : $\sigma^2 = \sum_x w_x (x - \bar{a})^2$, $\sigma = \sqrt{\sigma^2}$.
- Fonction de répartition : $F(a) = \sum_{x \leq a} w_x$.
- Quartiles par recherche du premier âge franchissant le seuil
  (`np.searchsorted` sur la CDF) :
  $Q_p = \min\{a : F(a) \geq p\}$ pour $p \in \{0{,}25 ; 0{,}50 ; 0{,}75\}$.
- Écart interquartile : $\mathrm{IQR} = Q_3 - Q_1$.

Voir [data/loader.py](data/loader.py) (`compute_percentiles_from_hmd`).

> **Décision** — Quartiles calculés sur la distribution des décès $d_x$ **plutôt
> que** sur les survivants $l_x$, **parce que** $d_x$ donne directement la densité
> des âges au décès dont on veut la médiane et la dispersion.

### 3.2 Interpolation de survie intra-cohorte — `interp_survival`

Les ancres `(âge, % vivants)` sont interpolées **linéairement** :

$$p(a) = p_0 + (p_1 - p_0)\,\dfrac{a - a_0}{a_1 - a_0}$$

Au-delà de la **dernière ancre**, prolongation de la pente du dernier segment,
bornée à $[0, 100]$ :

$$p(a) = \mathrm{clip}\!\left(p_n + \dfrac{p_n - p_{n-1}}{a_n - a_{n-1}}(a - a_n),\; 0,\; 100\right)$$

### 3.3 Interpolation inter-cohortes — `get_cohort_survival`

Pour une année de naissance située entre deux cohortes de référence `lo` et `hi`,
pondération linéaire des deux courbes interpolées :

$$p = p_{lo} + (p_{hi} - p_{lo})\, w, \qquad w = \dfrac{\text{naissance} - lo}{hi - lo}$$

Hors bornes, on retombe sur la cohorte de référence la plus proche. Voir
[common.py](common.py).

### 3.4 Effectifs de cohorte — page « Explorateur de cohorte »

$$\text{naissances}_{\text{sexe}} = \text{BIRTHS\_BY\_YEAR}[\text{année}] \times \text{SEX\_RATIO}[\text{sexe}]$$
$$\text{vivants} = \text{naissances} \times \dfrac{p(\text{âge actuel})}{100}, \qquad \text{âge actuel} = 2026 - \text{année de naissance}$$

L'espérance résiduelle affichée provient de `RESIDUAL_LIFE_2025` (table du moment),
interpolée à l'âge courant (plafonné à 95 ans). Voir
[pages/03_cohorte_explorer.py](pages/03_cohorte_explorer.py).

### 3.5 Décodage Eurostat JSON-stat — `fetch_eurostat_life_expectancy`

La réponse Eurostat est au format **JSON-stat** : un dictionnaire `value` indexé
par un entier linéaire. L'index est décodé par calcul des *strides* (produits
cumulés des tailles de dimensions) pour retrouver `(geo, sex)`, puis pivoté en
colonnes `e0_f`, `e0_m`, `e0_total`. Le code Eurostat `EL` (Grèce) est remappé en
`GR`, et `EU27_2020` en `EU`. Voir [data/loader.py](data/loader.py).

---

## 4. Hypothèses & choix délibérés

| Cas | Choix retenu | Justification |
|---|---|---|
| Fonctionnement sans compte HMD | Données embarquées par défaut | App utilisable hors-ligne ; API en option |
| Survie de cohorte | Interpolation linéaire d'ancres arrondies | Compacité, pas de credentials ; précision suffisante pour la pédagogie (±5 %) |
| Survie au-delà de la dernière ancre | Prolongation de la pente, bornée [0, 100] | Éviter les sauts ; rester dans un intervalle plausible |
| Espérance résiduelle | Table **du moment** 2025 (`RESIDUAL_LIFE_2025`) | Donnée disponible ; l'écran avertit qu'elle **sous-estime** la survie réelle des générations |
| Couleurs | Palette fixe par entité (femmes `#ec4899`, hommes `#0284c7`, e₀ `#f97316`) | Lecture cohérente entre les quatre pages ; jamais recyclée |
| Comparaison européenne | Eurostat 2024 embarqué, rafraîchissable | Instantané par défaut, actualisable à la demande |

> **Attention** — L'app affiche elle-même l'avertissement clé (page cohorte) : *les tables du
> moment sous-estiment historiquement la survie des générations* — l'espérance
> réelle d'une cohorte sera vraisemblablement **supérieure** si les progrès
> sanitaires se poursuivent.

---

## 5. Résultats chiffrés (données embarquées)

Valeurs lues dans `data/embedded.py` et `data/european.py` :

| Indicateur | Femmes | Hommes |
|---|---|---|
| e₀ en **1900** | **48,2 ans** | **43,4 ans** |
| e₀ en **2025** | **85,9 ans** | **80,3 ans** |
| Gain 1900→2025 | **+37,7 ans** | **+36,9 ans** |
| e₆₀ en 2025 | 28,0 ans | 23,5 ans |
| e₆₅ en 2025 | 23,6 ans | 19,7 ans |
| **IQR** des âges au décès 1900 → 2025 | **67 → 13 ans** | **65 → 17 ans** |

- **Écart femmes − hommes** (e₀ 2025) : **5,6 ans**.
- **Compression de la mortalité** : l'IQR féminin est divisé par ~5 (67 → 13 ans).
  En 1900, mourir à 5 ans ou à 75 ans était également banal ; en 2025 les décès se
  concentrent au-delà de 70 ans.
- **Comparaison européenne (Eurostat 2024)** : sur **26 pays**, e₀ totale de la
  **France = 83,0 ans**, au-dessus de la **moyenne UE-27 (81,5 ans)** ; en tête
  Espagne et Suède (**83,7 ans**). Les femmes françaises (**85,8 ans**) sont parmi
  les plus élevées d'Europe.

> Ces chiffres sont des **approximations embarquées**. Avec des credentials HMD ou
> un upload de table 1x1, la page « Distribution & variance » recalcule les
> **vrais** quartiles et l'écart-type et les superpose aux estimations.

---

## 6. Visualisations

Les graphiques sont **générés à la volée** par Plotly (aucun fichier image
statique n'est stocké dans le dépôt) :

| Page | Graphiques |
|---|---|
| Vue générale | Courbes e₀/e₆₀/e₆₅ 1900–2025 (repères WWI 1918, WWII 1945, Covid 2020) ; barres horizontales triées des 26 pays UE avec la France encadrée et la moyenne UE-27 ; deux tops 10 |
| Distribution & variance | Bande Q1–Q3 + médiane + e₀ ; aire d'évolution de l'IQR ; superposition quartiles HMD réels vs estimés (si import) |
| Explorateur de cohorte | Courbe de survie empilée (vivants / décédés cumulés) avec repère de l'âge courant |
| Âge fixe × générations | Aire du % encore en vie à âge fixe selon l'année d'observation, flèche de progression |

Le thème Plotly (`plotly_white` / `plotly_dark`) suit le thème Streamlit courant
(`apply_layout` dans [common.py](common.py)). Chaque page propose un export **CSV**
des données affichées (`download_csv`).

---

## 7. Pipeline d'exécution

```text
data/embedded.py  ─┐
data/european.py  ─┤─► common.py (interpolation, palette, thème) ─► pages/*.py ─► graphiques Plotly + métriques
data/loader.py  ──┘        (HMD API / upload / Eurostat API : rafraîchissement optionnel)
```

1. Chargement des constantes embarquées (repli) au démarrage.
2. `common.py` interpole les cohortes et fournit la palette / le template.
3. Chaque page construit ses `DataFrame` (avec `@st.cache_data`) et ses figures.
4. En option : `data/loader.py` télécharge HMD (credentials ou upload) et/ou
   interroge Eurostat pour remplacer les valeurs par défaut.

---

## 8. Limites de représentativité

- **Approximations, pas données brutes** : les valeurs par défaut sont des
  estimations arrondies (quartiles en années entières, effectifs au millier). La
  **survie de cohorte est annoncée à ±5 %**.
- **Ancres de cohorte éparses** : `COHORT_SURVIVAL` ne contient que quelques points
  `(âge, %)` par génération ; tout le reste est **interpolé linéairement**, et les
  âges au-delà de la dernière ancre sont **extrapolés** (pente du dernier segment).
- **Biais période vs génération** : l'espérance résiduelle et la distribution des
  âges au décès reposent sur des **tables du moment**. Elles décrivent une
  génération fictive soumise aux conditions d'une seule année et **sous-estiment**
  la survie réelle des cohortes en cours.
- **Périmètre géographique** : les naissances (`BIRTHS_BY_YEAR`) concernent la
  **France métropolitaine** ; la comparaison européenne est figée à **Eurostat
  2024** sauf rafraîchissement API.
- **Cohortes récentes tronquées** : pour les générations 1965–1990, les dernières
  ancres s'arrêtent à un âge jeune (la cohorte n'a pas encore vieilli), ce qui
  limite la portée des courbes de survie affichées.

---

## 9. Améliorations possibles (non implémentées)

| Piste | Bénéfice attendu |
|---|---|
| Basculer par défaut sur les vraies tables HMD (cache local) | Supprimer les approximations ±5 % |
| Construire de vraies tables de **génération** | Corriger le biais période sur la survie de cohorte |
| Intervalles de confiance / bandes d'incertitude | Rendre visible l'imprécision des estimations |
| Étendre la comparaison hors UE (HMD multi-pays) | Contexte mondial, pas seulement européen |
| Tests unitaires sur l'interpolation / le décodage JSON-stat | Fiabiliser `common.py` et `data/loader.py` |

---

## Licences & composants

| Composant | Rôle | Licence |
|---|---|---|
| Streamlit | Interface web multi-pages | Apache-2.0 |
| Plotly | Graphiques interactifs | MIT |
| pandas | Manipulation de tableaux | BSD-3-Clause |
| numpy | Calcul numérique (quartiles, variance) | BSD-3-Clause |
| requests | Appels API HMD / Eurostat | Apache-2.0 |
| ruff | Lint (groupe `dev`) | MIT |
| **Ce projet** | Code applicatif | MIT — Copyright (c) 2026 floSa |

**Données** : HMD (mortality.org, conditions d'utilisation propres — inscription
gratuite), Eurostat (réutilisation libre avec attribution), INSEE / DREES
(diffusion publique). Se reporter aux conditions de chaque fournisseur pour toute
réutilisation des données.
