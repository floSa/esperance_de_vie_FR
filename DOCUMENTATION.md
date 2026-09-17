# Documentation technique — Espérance de vie · France & Europe

Documentation méthodologique de l'application Streamlit d'analyse de l'espérance
de vie. Elle détaille le **problème étudié**, les **données** et leur provenance,
les **méthodes de calcul** (avec formules), les **hypothèses**, les **résultats
chiffrés** et, surtout, les **limites de représentativité**.

> Vue d'ensemble et démarrage : [README.md](README.md).

---

## 1. Problème étudié

L'application ne prédit rien : elle **décrit et met en scène** l'évolution de la
mortalité française et la compare au reste de l'Europe. Une question par page,
sept pages :

| Page | Question posée | Indicateur central |
|---|---|---|
| Vue générale | Comment l'espérance de vie a-t-elle évolué chez les femmes et les hommes ? | e₀ par sexe, 1946–2025 |
| Espérance de vie par âge | Combien d'années reste-t-il à vivre à un âge donné ? | Espérance résiduelle, 96 âges |
| Comparaison européenne | Où se situe la France dans l'UE ? | e₀ des 27 États membres |
| Distribution & variance | Les âges au décès se sont-ils resserrés autour d'un âge élevé ? | Quartiles Q1–Q3, IQR, écart-type |
| Explorateur de cohorte | Parmi les personnes nées une année donnée, combien sont encore en vie ? | Courbe de survie, effectifs |
| Survie à un âge donné | À âge constant, la survie s'améliore-t-elle d'une génération à l'autre ? | % vivants à âge fixe |
| Personnalités | Les personnalités meurent-elles plus âgées que l'ensemble des Français ? | Âge moyen au décès par période ; écart de chaque personnalité à son âge prédit |

**Vocabulaire démographique manipulé** :

| Terme | Sens |
|---|---|
| `e₀` | Espérance de vie **à la naissance** (années) |
| `e₆₀`, `e₆₅` | Espérance de vie **résiduelle** à 60 / 65 ans |
| Table **du moment** (période) | Mortalité observée une année donnée, appliquée à tous les âges — une génération *fictive* |
| Table de **génération** (cohorte) | Mortalité réellement subie par les personnes nées la même année |
| `dx` | Nombre de décès par âge dans une table de mortalité — la densité des âges au décès |
| IQR | Écart interquartile `Q3 − Q1` : fenêtre d'âge contenant **50 %** des décès |

**Difficulté spécifique** : distinguer la logique **période** de la logique
**génération**. Une table du moment mesure les conditions de mortalité d'une
année ; elle ne décrit **aucune personne réelle** de bout en bout. Une table de
génération suit une cohorte, mais reste incomplète tant que la cohorte n'est pas
éteinte. L'app manipule les deux et l'affiche explicitement.

---

## 2. Données & provenance

Toutes les données téléchargeables sont **régénérées par script**, jamais saisies
à la main :

```bash
uv run python -m scripts.refresh_data
```

### 2.1 Les huit jeux de données

| Jeu (`data/sources/`) | Source | Jeu de données | Couverture |
|---|---|---|---|
| `esperance_vie_fr_insee.csv` | INSEE, API Melodi | `DS_DECES_MORTALITE_SERIES`, `EC_MEASURE=LEXPEC` | 1946–2025, sexes F/M, âges 0·1·20·40·60 |
| `esperance_vie_fr_tous_ages_eurostat.csv` | Eurostat | `demo_mlexpec`, tous âges | 1998–2024, sexes F/M, âges 0 à 95 |
| `esperance_vie_fr_longue_owid.csv` | Our World in Data (relais HMD) | `grapher/life-expectancy` | 1816–2023, tous sexes |
| `naissances_fr_insee.csv` | INSEE, API Melodi | `DS_NAISSANCES_FECONDITE_SERIES`, `LVB_PLACE_REG` | 1901–2025 |
| `distribution_deces_eurostat.csv` | Eurostat | `demo_mlifetable`, `indic_de=NUMBERDYING` (`dx`) | 2014–2024, sexes F/M |
| `esperance_vie_europe_eurostat.csv` | Eurostat | `demo_mlexpec`, `age=Y_LT1` | dernière année publiée, 41 territoires |
| `deces_par_age_eurostat.csv` | Eurostat | `demo_magec`, décès enregistrés par âge (100 = 100 ans et plus) | 1986–2024, sexes F/M ; `FX` avant 1998, `FR` ensuite |
| `deces_personnalites_wikidata.csv` | Wikidata, via le projet `deces_personnalites_FR` | personnes de nationalité française ayant au moins un article Wikipédia | 1990–2025, âge exact au décès |

Aucune de ces sources ne demande de compte ni de clé d'API.

**Les personnalités font exception au rafraîchissement direct.** Leur collecte
sur Wikidata prend plus d'une demi-heure (le service public coupe toute requête
au-delà de 60 secondes, les années sont découpées en tranches). Elle vit dans le
projet voisin `deces_personnalites_FR` ; `refresh_data` en importe le fichier
consolidé, en ne gardant que les personnes dont l'âge au décès est calculable
au jour près et dont le sexe est renseigné (27 785 sur 29 560).

### 2.2 Le manifeste de provenance

Chaque rafraîchissement réécrit `data/sources/manifest.json`. Pour chaque jeu :

```json
{
  "fichier": "esperance_vie_fr_insee.csv",
  "fournisseur": "INSEE",
  "jeu": "DS_DECES_MORTALITE_SERIES (EC_MEASURE=LEXPEC)",
  "url": "https://api.insee.fr/melodi/data/DS_DECES_MORTALITE_SERIES",
  "parametres": { "FREQ": "A", "EC_MEASURE": "LEXPEC", "GEO": "2025-FRANCE-FM" },
  "annees": "1946–2025",
  "lignes": 800,
  "extrait_le": "2026-09-16T08:45:07+00:00"
}
```

Les jeux Eurostat portent en plus `millesime_source`, la date de mise à jour que
le fournisseur déclare lui-même. C'est ce champ qui permet de savoir si une
absence de données est un bug ou une non-publication.

> **Décision** — *CSV + manifeste versionnés* **plutôt que** téléchargement au
> démarrage de l'app, **parce que** l'app doit se lancer hors-ligne et que le
> diff Git des CSV rend visible ce qui a changé entre deux millésimes.
> **Limite** : les données ne sont à jour que du dernier `refresh_data`.

### 2.3 Périmètre géographique

Le périmètre retenu côté INSEE est **France métropolitaine**
(`GEO=2025-FRANCE-FM`), constant sur toute la profondeur historique. « France
entière » intègre les DOM à partir de 1990 et introduirait une rupture de série
au milieu de la période étudiée.

Pour les naissances, la mesure retenue est le **lieu d'enregistrement**
(`LVB_PLACE_REG`, 1901–2025) et non le lieu de résidence (`LVB_PLACE_RES`), qui
ne commence qu'en 1975 — les mélanger créerait une discontinuité en plein milieu
des cohortes étudiées.

### 2.4 Ce qui reste estimé (`data/embedded.py`)

| Constante | Forme | Pourquoi pas de source ouverte |
|---|---|---|
| `COHORT_SURVIVAL` | `{sexe: {année_naissance: [(âge, % vivants), …]}}`, 1930→1990 | Aucune institution ne publie de tables de mortalité **par génération** pour la France |
| `PERIOD_DISTRIBUTION_FEMMES` / `_HOMMES` | `{year, e0, q1, median, q3, iqr}`, 1900→2010 | Eurostat ne remonte pas avant 2014 |
| `RESIDUAL_LIFE_2025` | `{sexe: {âge: années restantes}}` | Reliquat : Eurostat publie désormais tous les âges, cette table peut être remplacée (§ 9) |
| `SEX_RATIO` | `femmes 0,487 · hommes 0,513` | Constante démographique |

Précision annoncée : **±5 %** sur la survie par génération.

---

## 3. Méthodes de calcul

### 3.1 Quartiles des âges au décès, depuis `dx`

Pour chaque année, à partir du nombre de décès `dx` par âge de la table de
mortalité :

- Poids normalisés : $w_x = \dfrac{d_x}{\sum_x d_x}$ (avec $d_x$ borné à $\geq 0$).
- Âge moyen au décès : $\bar{a} = \sum_x w_x \, x$.
- Variance / écart-type : $\sigma^2 = \sum_x w_x (x - \bar{a})^2$, $\sigma = \sqrt{\sigma^2}$.
- Fonction de répartition : $F(a) = \sum_{x \leq a} w_x$.
- Quartiles par recherche du premier âge franchissant le seuil
  (`np.searchsorted` sur la CDF) :
  $Q_p = \min\{a : F(a) \geq p\}$ pour $p \in \{0{,}25 ; 0{,}50 ; 0{,}75\}$.
- Écart interquartile : $\mathrm{IQR} = Q_3 - Q_1$.

Voir `_quantiles_from_dx` dans [scripts/sources.py](scripts/sources.py).

> **Décision** — Quartiles calculés sur la distribution des décès $d_x$ **plutôt
> que** sur les survivants $l_x$, **parce que** $d_x$ donne directement la densité
> des âges au décès dont on veut la médiane et la dispersion.

### 3.2 Interpolation de survie intra-génération — `interp_survival`

Les ancres `(âge, % vivants)` sont interpolées **linéairement** :

$$p(a) = p_0 + (p_1 - p_0)\,\dfrac{a - a_0}{a_1 - a_0}$$

Au-delà de la **dernière ancre**, la fonction retourne `None`. Elle ne prolonge
plus la pente du dernier segment : pour les générations récentes, cette dernière
ancre correspond à l'âge atteint aujourd'hui, et le segment final ne couvre
parfois qu'une seule année — une pente beaucoup trop raide pour être extrapolée
sur plusieurs décennies.

### 3.3 Interpolation inter-générations — `get_cohort_survival`

Seules les générations de référence **ayant réellement atteint l'âge demandé**
participent au calcul :

$$\mathcal{C}(a) = \{\, c : \text{âge de la dernière ancre de } c \geq a \,\}$$

Pour une année de naissance encadrée par deux générations $lo$ et $hi$ de
$\mathcal{C}(a)$, pondération linéaire des deux courbes :

$$p = p_{lo} + (p_{hi} - p_{lo})\, w, \qquad w = \dfrac{\text{naissance} - lo}{hi - lo}$$

Au-delà de la génération la plus récente de $\mathcal{C}(a)$, **on retient sa
valeur telle quelle**, sans extrapoler la tendance entre générations. Si
$\mathcal{C}(a)$ est vide, la fonction retourne `None`.

`age_max_documente(sexe)` donne l'âge le plus élevé pour lequel une valeur
existe — 95 ans. Les pages doivent s'y borner : la génération 1930 a dépassé
cet âge, et lui demander sa survie à son âge réel renvoie `None`.

> **Décision** — *Pas d'extrapolation entre générations* **plutôt que**
> prolongation de la tendance, **parce que** cette dernière amplifiait un écart
> de 5 années de naissance sur 10 ans de projection et produisait une survie qui
> **remontait avec l'âge**. **Limite** : la progression des générations les plus
> récentes est légèrement sous-estimée, la courbe s'aplatissant sur son dernier
> segment.

### 3.4 Effectifs de cohorte — page « Explorateur de cohorte »

$$\text{naissances}_{\text{sexe}} = \text{naissances}[\text{année}] \times \text{SEX\_RATIO}[\text{sexe}]$$
$$\text{vivants} = \text{naissances} \times \dfrac{p(a^{*})}{100}, \qquad a^{*} = \min(\text{âge actuel},\; 95)$$

avec $\text{âge actuel} = \text{année courante} - \text{année de naissance}$.
Le plafond $a^{*}$ vient de `age_max_documente()` : les générations nées avant
1931 ont dépassé le dernier âge documenté. La page affiche alors l'âge
réellement utilisé et signale l'écart.

L'espérance résiduelle provient de `RESIDUAL_LIFE_2025` (table du moment),
interpolée à l'âge courant, et présentée sous forme d'**âge de décès moyen
attendu** : $\text{âge actuel} + e_{\text{résiduelle}}$.

### 3.5 Décodage Eurostat JSON-stat — `_jsonstat`

La réponse Eurostat est au format **JSON-stat 2.0** : un dictionnaire `value`
indexé par un entier linéaire. L'index est décodé par calcul des *strides*
(produits cumulés des tailles de dimensions) pour retrouver le n-uplet de
dimensions `(geo, sex, age, time, …)`. Le décodeur est générique et sert aux
quatre appels Eurostat du projet. Voir [scripts/sources.py](scripts/sources.py).

### 3.6 Comparaison personnalités / population — `comparaison_age_deces`

Pour une période $P$ de 5 ans, un sexe et un âge minimal $a_{\min} = 25$ :

$$\bar{a}_{\text{pop}}(P) = \dfrac{\sum_{t \in P} \sum_{a \geq a_{\min}} a \cdot D_{t,a}}{\sum_{t \in P} \sum_{a \geq a_{\min}} D_{t,a}}$$

où $D_{t,a}$ est le nombre de décès enregistrés l'année $t$ à l'âge $a$
(Eurostat `demo_magec`). Côté personnalités, simple moyenne des âges exacts au
décès des personnes mortes pendant $P$, au même âge minimal.

Seules les années couvertes par les deux sources entrent dans le calcul
(1990–2024) ; `bilan_age_deces` applique le même calcul à toute cette période.

> **Décision** — *Comparer à l'âge au décès des Français morts la même période*
> **plutôt qu'**à l'espérance de vie, **parce que** les deux côtés décrivent
> alors la même chose : des décès réels. L'espérance de vie à la naissance
> décrit une génération fictive et inclut la mortalité infantile.

> **Décision** — *Décès à 25 ans ou plus, des deux côtés*, **parce qu'**on
> devient rarement célèbre enfant. Garder les décès d'enfants dans la population
> seule abaisserait artificiellement son âge moyen au décès.

### 3.7 Âge prédit d'une personnalité — `ecarts_personnalites`

Pour une personne de sexe $s$, née l'année $n$ et morte à l'âge $a \geq 60$ :

$$\hat{a} = 60 + e_{60}(n + 60,\; s), \qquad \text{écart} = a - \hat{a}$$

où $e_{60}(t, s)$ est l'espérance de vie à 60 ans publiée par l'INSEE pour
l'année $t$. Un écart positif signifie un décès après l'âge prédit.

Le même calcul est appliqué à tous les décès enregistrés (`ecarts_population`),
en déduisant l'année des 60 ans de l'année et de l'âge au décès, et en pondérant
par le nombre de décès. Le groupe « 100 ans et plus » est gardé à 100 ans.

> **Décision** — *Prédire à 60 ans* **plutôt qu'**à la naissance, **parce
> que** l'INSEE ne publie l'espérance de vie qu'à partir de 1946 (seules 14 % des
> personnalités seraient comparables), et que l'espérance à la naissance compte
> les décès d'enfants, auxquels toute personnalité a survécu. **Limite** : les
> personnalités mortes avant 60 ans n'ont pas d'âge prédit (2 289 hommes et
> femmes sur 1990–2024) ; la page les dénombre.

> **Décision** — *Afficher la même mesure pour l'ensemble des Français*,
> **parce que** $e_{60}$ vient d'une table du moment : la mortalité ayant
> continué de baisser après l'année des 60 ans, la plupart des gens dépassent
> leur âge prédit. Sans cette référence, « 67 % après la prédiction » ferait
> croire à un effet bien plus fort qu'il n'est.

### 3.8 Authentification HMD

HMD n'est **pas** utilisé par défaut, Eurostat fournissant les mêmes quantités
en accès libre depuis 2014. La fonction `hmd_session()` reste disponible pour
qui veut remonter avant 2014 avec un compte gratuit :

```bash
export HMD_USER="votre@email.com"
export HMD_PASSWORD="motdepasse"
uv run python -m scripts.refresh_data --hmd
```

mortality.org est une application ASP.NET Core : l'authentification HTTP Basic
n'y fonctionne pas — elle renvoie un **200 OK contenant le formulaire de
connexion**. Il faut récupérer le jeton `__RequestVerificationToken` sur la page
de login, poster le formulaire, puis réutiliser la session. Le code vérifie le
`content-type` des réponses pour ne jamais confondre une page HTML avec une
table de mortalité.

---

## 4. Hypothèses & choix délibérés

| Cas | Choix retenu | Justification |
|---|---|---|
| Fraîcheur des données | CSV versionnés, régénérés par script | App utilisable hors-ligne ; provenance vérifiable ; diff Git lisible |
| Source des quartiles | Eurostat `demo_mlifetable` | Mêmes quantités que HMD, sans compte ni fichier à importer |
| Profondeur avant 1946 | OWID, tous sexes confondus | Seule source ouverte continue ; le détail par sexe n'existe pas avant |
| Survie au-delà de la dernière ancre | `None`, aucune extrapolation | L'extrapolation produisait des valeurs démographiquement impossibles |
| Espérance résiduelle | Table **du moment** 2025 | Donnée disponible ; l'écran avertit qu'elle **sous-estime** la survie réelle |
| Couleurs | Palette fixe par entité (femmes `#ec4899`, hommes `#0284c7`, e₀ `#f97316`) | Lecture cohérente entre les sept pages ; jamais recyclée |
| Année courante | Dérivée de `date.today()` | Évite une péremption silencieuse au 1ᵉʳ janvier |
| Personnalités : point de comparaison | Âge au décès des Français morts la même période | Comparer des décès à des décès (§ 3.6) |
| Personnalités : âge minimal | 25 ans, des deux côtés | Neutraliser la mortalité infantile, absente chez les personnalités |
| Personnalités : sexe | Toujours séparé | 83 % des personnalités sont des hommes, qui meurent plus jeunes |
| Personnalités : définition | Au moins un article Wikipédia, toutes langues | Sans ce filtre, un tiers des fiches Wikidata ne sont pas des personnalités publiques |
| Personnalités : âge prédit | 60 ans + espérance de vie à 60 ans l'année des 60 ans (§ 3.7) | Couvre 92 % des personnalités, sans biais de mortalité infantile |
| Personnalités : référence | Même mesure sur tous les décès | La prédiction est dépassée par la majorité de la population elle-même |
| Découpage des pages | Une question, une source, une période par page | Une figure mêlant deux périmètres est illisible : c'est ce qui a motivé le passage de quatre à six, puis sept pages |
| Axe des années, page « par âge » | Fixé à 1998–2024 quel que soit l'âge | Un axe qui bouge avec le sélecteur rend deux sélections incomparables |
| Survie au-delà du dernier âge documenté | Affichage borné, écart signalé | Mieux vaut afficher moins que d'inventer une valeur |
| Sélecteur de sexe | Liste déroulante sur les trois pages concernées | Un seul geste à apprendre |

> **Attention** — L'app affiche elle-même l'avertissement clé (page cohorte) :
> *les tables du moment sous-estiment historiquement la survie des générations*.
> L'espérance réelle d'une cohorte sera vraisemblablement **supérieure** si les
> progrès sanitaires se poursuivent.

---

## 5. Résultats chiffrés

Valeurs issues de `data/sources/`, extraction du 16 septembre 2026.

| Indicateur | Femmes | Hommes |
|---|---|---|
| e₀ en **1946** | **65,2 ans** | **59,9 ans** |
| e₀ en **2025** | **85,9 ans** | **80,4 ans** |
| Gain 1946→2025 | **+20,7 ans** | **+20,5 ans** |
| e₆₀ en 2025 | 28,0 ans | 23,9 ans |
| e₆₅ en 2024 | 23,6 ans | 19,9 ans |
| IQR des âges au décès, 2024 (mesuré) | **12 ans** (78 → 90) | **17 ans** (71 → 88) |
| Écart-type des âges au décès, 2024 | 13,5 ans | 15,1 ans |

Série longue tous sexes confondus (OWID) : **40,1 ans en 1816**, 45,1 en 1900,
**34,8 en 1918**, 66,4 en 1950, 83,3 en 2023.

- **Écart femmes − hommes** (e₀ 2025) : **5,5 ans**.
- **Creux de 1918** : l'espérance de vie chute de 43,0 ans (1917) à **34,8 ans**,
  sous l'effet conjugué de la guerre et de la grippe espagnole, puis remonte
  immédiatement — illustration directe de ce qu'une table du moment mesure.
- **Compression de la mortalité** : l'IQR féminin passe d'environ 67 ans en 1900
  (estimation) à **12 ans en 2024** (mesuré).
- **Comparaison européenne (Eurostat 2024)** : sur les **27 États membres**,
  France **83,0 ans**, au-dessus de la **moyenne UE-27 (81,5 ans)** ; en tête
  l'**Espagne (84,0 ans)** puis la **Suède (83,8 ans)**.

| Âge moyen au décès, 1990–2024, décès à 25 ans ou plus | Personnalités | Ensemble | Écart |
|---|---|---|---|
| Hommes (22 504 personnalités) | 79,7 ans | 73,6 ans | **+6,1 ans** |
| Femmes (4 372 personnalités) | 81,9 ans | 81,4 ans | **+0,5 an** |

- **Hommes** : l'écart est stable, entre 5,6 et 6,6 ans selon la période.
- **Femmes** : pas d'écart réel ; il devient même légèrement négatif sur
  2015–2024 (−0,2 et −0,3 an).

| Décès après l'âge prédit à 60 ans, 1990–2024 | Personnalités | Ensemble | Écart médian (personnalités / ensemble) |
|---|---|---|---|
| Hommes | **67 %** | 53 % | +5,4 ans / +1,0 an |
| Femmes | **63 %** | 61 % | +4,0 ans / +3,2 ans |

---

## 6. Visualisations

Les graphiques sont **générés à la volée** par Plotly (aucun fichier image
statique dans le dépôt). **Chaque graphique porte une note « Comment lire ce
graphique »** qui explique les axes, le sens d'une variation et le piège
éventuel — rendue par `note_lecture()` dans [common.py](common.py).

| Page | Graphiques |
|---|---|
| Vue générale | Courbes e₀ femmes / hommes 1946–2025 ; série longue 1816–2023, sexes réunis, avec repères 1871, 1918, 1940 |
| Espérance de vie par âge | Courbes femmes / hommes pour l'âge choisi au curseur (0 à 95 ans), axe des années fixé à 1998–2024 |
| Comparaison européenne | Barres horizontales triées des 27 pays UE, France cerclée, moyenne UE-27 ; deux tops 10 |
| Distribution & variance | Bande Q1–Q3 + médiane + e₀, avec repère visuel de la frontière estimé / mesuré ; aire d'évolution de l'IQR |
| Explorateur de cohorte | Courbe de survie empilée (vivants / décédés cumulés) avec repère de l'âge courant |
| Survie à un âge donné | Aire du % encore en vie à âge fixe selon l'année d'observation, flèche de progression |
| Personnalités | Barres groupées par période de 5 ans : âge moyen au décès de l'ensemble (gris) et des personnalités (couleur du sexe) ; graphique en haltères des 30 personnalités les plus connues de la période (âge prédit → âge réel, vert après, rouge avant) ; histogramme des écarts à l'âge prédit, personnalités en barres, ensemble en ligne |

Le thème Plotly (`plotly_white` / `plotly_dark`) suit le thème Streamlit courant
(`apply_layout`). Chaque page propose un export **CSV** (`download_csv`).

---

## 7. Pipeline d'exécution

```text
APIs publiques ──► scripts/refresh_data.py ──► data/sources/*.csv + manifest.json
(INSEE, Eurostat,          ▲                             │
 Our World in Data)        │                             ▼
Wikidata ──► projet deces_personnalites_FR (collecte longue, import du CSV)
                                              data/repository.py
                                                         │
                     data/embedded.py ───────────────────┤
                  (survie par génération)                ▼
                                          common.py (interpolation, palette, thème)
                                                         │
                                                         ▼
                                            pages/*.py ──► figures Plotly + métriques
```

1. `refresh_data.py` interroge les API et écrit les CSV **et** le manifeste.
2. `repository.py` lit ces CSV (mise en cache `lru_cache`), assemble les séries
   et expose `millesime()` pour afficher la provenance sous les graphiques.
3. `embedded.py` fournit ce qu'aucune API ne publie.
4. `common.py` interpole les générations et fournit palette, thème et notes de
   lecture.
5. Chaque page construit ses `DataFrame` (avec `@st.cache_data`) et ses figures.

---

## 8. Limites de représentativité

- **Survie par génération estimée** : `COHORT_SURVIVAL` ne contient que quelques
  ancres `(âge, %)` par génération, interpolées linéairement. Précision annoncée
  **±5 %**. C'est la limite la plus forte du projet, et elle est structurelle :
  aucune source ouverte ne publie ces tables pour la France.
- **Quartiles avant 2014 estimés** : la page « Distribution & variance » mélange
  deux régimes, séparés visuellement par un repère. Les valeurs estimées
  s'écartent des valeurs mesurées de plusieurs années sur Q3.
- **Détail par sexe absent avant 1946** : la profondeur historique n'existe qu'en
  « tous sexes confondus » (OWID).
- **Générations récentes plafonnées** : au-delà de la dernière génération ayant
  atteint un âge donné, la valeur est reprise telle quelle. La courbe s'aplatit
  sur son dernier segment plutôt que de poursuivre sa progression — choix
  conservateur assumé (§ 3.3).
- **Biais période vs génération** : l'espérance résiduelle et la distribution des
  âges au décès reposent sur des **tables du moment**. Elles décrivent une
  génération fictive soumise aux conditions d'une seule année et **sous-estiment**
  la survie réelle des cohortes en cours.
- **Générations les plus anciennes tronquées** : les tables de survie s'arrêtent
  à 95 ans. Les générations nées avant 1931 ont dépassé cet âge ; l'explorateur
  de cohorte affiche alors les effectifs à 95 ans et le signale.
- **Espérance de vie par âge limitée à 1998** : Eurostat, seule source couvrant
  les 96 âges, ne remonte pas plus loin. Les onze âges de 85 à 95 ans ne
  commencent même qu'en 2014.
- **Personnalités, biais de sélection** : un écart d'âge au décès ne prouve pas
  que la célébrité fait vivre plus longtemps. Vivre longtemps laisse le temps de
  devenir connu ; les personnalités sont aussi en moyenne plus diplômées et plus
  aisées, deux facteurs qui allongent la vie par eux-mêmes.
- **Personnalités, définition** : « française » au sens de la nationalité
  Wikidata, doubles nationaux inclus ; « personnalité » au sens d'au moins un
  article Wikipédia. La complétude dépend des contributeurs, et les décès les
  plus récents sont sous-représentés.
- **Âge prédit issu d'une table du moment** : il sous-estime la survie réelle.
  C'est pourquoi la page le compare toujours au même calcul fait sur l'ensemble
  des Français, et jamais à zéro. Les personnalités mortes avant 60 ans en sont
  exclues.
- **Population, rupture de périmètre en 1998** : France métropolitaine avant,
  France entière ensuite. Les DOM pèsent environ 2 % des décès.
- **Millésime figé** : les données ne sont à jour que du dernier
  `refresh_data` — date d'extraction consultable dans le manifeste et affichée
  sous chaque graphique.

---

## 9. Améliorations possibles (non implémentées)

| Piste | Bénéfice attendu |
|---|---|
| Intégrer les tables HMD 1×1 par défaut (compte + cache local) | Quartiles réels avant 2014, détail par sexe avant 1946 |
| Construire de vraies tables de **génération** à partir des tables 1×1 | Supprimer l'approximation ±5 %, la limite la plus forte du projet |
| Dériver `RESIDUAL_LIFE_2025` d'Eurostat `demo_mlexpec` (tous âges) | Remplacer la dernière table saisie à la main |
| Intervalles de confiance / bandes d'incertitude | Rendre visible l'imprécision des estimations |
| Espérance de vie **par département** (INSEE publie `LEXPEC` par DEP) | Dimension territoriale, déjà accessible sans travail de collecte |
| Rafraîchissement automatique par la CI (cron mensuel + PR) | Supprimer l'étape manuelle de mise à jour |

---

## 10. Qualité & reprise

```bash
uv run ruff check .                     # lint
uv run pytest -q                        # invariants démographiques
uv run python scripts/check_pages.py    # rendu des 8 pages
```

Les tests de [tests/test_survie_cohorte.py](tests/test_survie_cohorte.py) portent
sur des **propriétés**, pas sur des valeurs : la survie décroît avec l'âge, elle
ne régresse pas d'une génération à la suivante (tolérance 0,5 point, l'arrondi
des ancres étant à ±5 %), elle reste dans [0, 100], et aucune génération ne se
voit attribuer de survie à un âge qu'elle n'a pas atteint. Un dernier test
vérifie que `age_max_documente()` reste exploitable par toutes les générations
du curseur.

Ce sont ces invariants qui ont mis au jour le creux de survie artificiel des
générations 1963–1967, et deux ancres corrompues de la génération 1965.

Les tests de
[tests/test_comparaison_personnalites.py](tests/test_comparaison_personnalites.py)
verrouillent la méthode de la page Personnalités sur des données synthétiques :
même seuil d'âge des deux côtés, moyenne de la population pondérée par les
décès, période limitée aux années communes, sexes séparés, âge prédit pris
l'année des 60 ans et sur la seule source INSEE, personnalités mortes avant
60 ans écartées et dénombrées.

La CI ([.github/workflows/ci.yml](.github/workflows/ci.yml)) exécute les trois
commandes ci-dessus à chaque push et chaque pull request.

---

## Licences & composants

Code sous **MIT** — voir [LICENSE](LICENSE). Les **données** relèvent des
conditions de leurs producteurs : Licence Ouverte Etalab (INSEE), politique de
réutilisation de la Commission européenne (Eurostat), CC BY 4.0 (Our World in
Data, relayant HMD).

| Composant | Rôle | Licence |
|---|---|---|
| Streamlit | Interface web multi-pages | Apache-2.0 |
| Plotly | Graphiques interactifs | MIT |
| pandas | Manipulation de tableaux | BSD-3-Clause |
| numpy | Calcul numérique (quartiles, variance) | BSD-3-Clause |
| requests | Appels aux API | Apache-2.0 |
| ruff · pytest | Lint et tests (groupe `dev`) | MIT |
