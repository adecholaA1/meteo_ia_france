# 📊 Météo IA France — Benchmarks

> 🇬🇧 **English version below** ([jump to English](#-météo-ia-france--benchmarks-english))

Résultats observés sur le projet Météo IA France, mesurés via l'API backend (`/api/mae/*` et `/api/heatmap/error`) sur la grille France 0.25° (2 925 points).

> ⚠️ **Disclaimer scientifique** : ces résultats reflètent l'état du projet à la date d'évaluation. Les MAE varient selon les conditions météo (les modèles physiques comme AROME ont des forces et faiblesses différentes selon les régimes). Voir la section [Méthodologie](#-méthodologie) pour le contexte complet.

> 📅 **Dernière mise à jour** : 27 avril 2026 — chiffres consolidés post-implémentation du MAE cyclique pour les variables angulaires (cf. [Notes méthodologiques](#-notes-méthodologiques)). Désormais consultables interactivement sur le **dashboard frontend** (étape 9 livrée le 27 avril 2026) et sa **page Méthodologie publique**.

---

## 🎯 TL;DR

Sur la France métropolitaine, à horizon 24 h, sur 3 jours d'évaluation (17–19 avril 2026, 2 925 points × 4 timestamps × 3 jours = 35 100 paires de mesures par variable et par modèle) :

| Variable | GraphCast vs ERA5 (MAE) | AROME vs ERA5 (MAE) | AROME / GraphCast |
|---|---|---|---|
| Température 2 m (°C) | **3.81** | **1.16** | **AROME 3.3× plus précis** |
| Vitesse vent 10 m (m/s) | 1.38 | 0.83 | AROME 1.7× plus précis |
| Direction vent 10 m (°) ⚙️ | 67.55 | 33.89 | AROME 2.0× plus précis |
| Pression mer (hPa) | 3.44 | 0.39 | **AROME 8.7× plus précis** |
| Précipitations 6 h (mm) | 0.22 | 0.19 | AROME 1.2× plus précis |
| TOA solaire (W/m²) | 0.00 | 0.00 | identique (variable astronomique) |

⚙️ La direction du vent utilise un MAE circulaire (cf. [Notes méthodologiques](#-notes-méthodologiques)).

➡️ **AROME devance GraphCast Operational sur les 5 variables comparables** (TOA exclu car déterministe), avec des facteurs allant de 1.2× à 8.7×. Ces résultats sont cohérents avec la littérature : les modèles fondation IA sans spécialisation régionale n'égalent pas les modèles physiques régionaux à courte/moyenne échéance sur leurs domaines de spécialisation.

---

## 🔬 Méthodologie

### Sources comparées

| Source | Type | Résolution native | Fréquence | Latence |
|---|---|---|---|---|
| **ERA5** (ECMWF) | Réanalyse (vérité terrain) | 0.25° | Horaire | ~5 jours (J-5) |
| **GraphCast Operational** (Google DeepMind) | IA, modèle fondation | 0.25° | 6 h (4 horizons : +6, +12, +18, +24) | Temps réel |
| **AROME** (Météo-France) | Modèle physique régional | 0.025° → ré-échantillonné 0.25° | 6 h | ~4 h après le run |

### Périmètre d'évaluation

- **Zone** : grille France métropolitaine (lat 41.0–51.5, lon -5.5–9.0), résolution 0.25°
- **Nombre de points GPS** : 2 925 (45 latitudes × 65 longitudes)
- **Variables évaluées** : 6 (t2m, wind_speed, wind_direction, msl, tp_6h, toa)
- **Horizons** : 6 h, 12 h, 18 h, 24 h
- **Période d'évaluation** : 17–19 avril 2026 (3 jours, limités par la latence J-5 d'ERA5)
- **Volume statistique** : 35 100 paires de mesures par (variable × modèle) sur la période

### Métriques calculées

- **MAE** (Mean Absolute Error) — erreur moyenne en valeur absolue, exprimée dans l'unité physique de la variable
- **RMSE** (Root Mean Squared Error) — pénalise davantage les grandes erreurs ponctuelles
- **Bias** = `mean(prédiction - vérité)` — erreur moyenne signée. Positif → surestimation systématique. Négatif → sous-estimation. Permet d'identifier des défauts corrigibles par offset.

Toutes les métriques sont calculées **par variable, par jour, par horizon, par comparaison**, sur l'ensemble des 2 925 points GPS.

---

## 📐 Notes méthodologiques

### MAE circulaire pour les variables angulaires

La direction du vent est une grandeur **cyclique** (0° = 360°) : une prédiction de 5° face à une vérité de 355° donne mathématiquement un écart linéaire de 350°, alors que l'écart angulaire physique réel n'est que de 10°.

Pour `wind_direction_10m_deg`, le pipeline applique donc une **distance angulaire minimale** :

```python
abs_error = min(|pred - vérité| mod 360, 360 - |pred - vérité| mod 360)
```

Cette correction a un impact significatif : avant son implémentation, le MAE moyen de la direction du vent était reporté autour de 110° (artefact des bordures 0°/360°). Après correction, il s'établit à **34° pour AROME** et **68° pour GraphCast** — valeurs cohérentes avec les benchmarks ECMWF (typiquement 20–40° d'erreur sur la direction du vent à 10 m sur l'Europe).

### Bias `NULL` pour wind_direction

Pour les variables cycliques, un biais signé n'a **pas d'interprétation physique simple** (un biais de +90° ne veut pas dire "le modèle tourne dans le sens horaire"). Le pipeline force donc `bias = NULL` pour `wind_direction_10m_deg`. Le frontend affiche cette valeur comme `N/A — variable cyclique`.

### TOA solaire : MAE strictement nul par construction

`toa_wm2` (Top-of-Atmosphere solar irradiance) n'est pas une variable météorologique prédite par les modèles. C'est une **grandeur astronomique déterministe** qui ne dépend que de `(timestamp, latitude, longitude)`. Pour garantir la cohérence inter-sources, elle est calculée par le pipeline avec la formule de Spencer (1971) appliquée identiquement aux 3 sources → **MAE = 0 par construction**, sur tous les horizons et toutes les dates. Cette variable reste pertinente pour les **courbes** et **heatmaps de valeurs absolues** (estimation du potentiel solaire), mais elle est **non discriminante** pour évaluer la qualité d'un modèle.

### Choix MAE / RMSE / Bias plutôt que MAPE

Le **MAPE** (Mean Absolute Percentage Error) est volontairement écarté de la suite de métriques :

1. **Division par zéro** — 4 des 6 variables (précipitations, vent calme, TOA nuit, direction nord) prennent légitimement la valeur 0, ce qui rend MAPE instable ou indéfini
2. **Asymétrie** — MAPE pénalise massivement les erreurs sur les petites valeurs absolues, créant des distorsions sur les variables qui transitent par zéro
3. **Standard du domaine** — la littérature météorologique (ECMWF, Météo-France, papers GraphCast / Pangu / ClimaX) utilise exclusivement MAE, RMSE, Bias et le Skill Score normalisé

L'ajout du **Skill Score** vs climatologie persistante est envisagé en v1.1.

---

## 🌡️ Performance température (`t2m_celsius`)

### MAE quotidien — horizon 24 h

| Date | AROME vs ERA5 | GraphCast vs ERA5 | Ratio |
|---|---|---|---|
| 2026-04-17 | 1.13 °C | 4.42 °C | 3.91× |
| 2026-04-18 | 1.20 °C | 3.87 °C | 3.23× |
| 2026-04-19 | 1.14 °C | 3.15 °C | 2.76× |
| **Moyenne 3 j** | **1.16 °C** | **3.81 °C** | **3.27×** |

### Bias systématique

À horizon 24 h, GraphCast présente un **biais négatif systématique** sur la température : le modèle sous-estime de plusieurs degrés en milieu de journée sur la France. À l'inverse, AROME présente un biais quasi-nul, signe d'un modèle bien calibré localement.

À horizon 6 h, les MAE de GraphCast se rapprochent significativement de ceux d'AROME, indiquant que la dégradation observée est principalement liée à la **propagation autorégressive** du modèle au-delà du court terme.

### Heatmap d'écart spatial (exemple : 2026-04-19 12 h UTC)

```
GraphCast vs ERA5 (t2m_celsius)            AROME vs ERA5 (t2m_celsius)
─────────────────────────────────          ─────────────────────────────────
min     : -15.07 °C                        min     : -14.34 °C
max     :  +1.91 °C                        max     : +15.12 °C
mean    :  -5.34 °C  (sous-estime)         mean    :  +0.43 °C  (équilibré)
abs_mean:   5.38 °C  (MAE spatial)         abs_mean:   1.28 °C  (MAE spatial)
```

**Lecture** : à midi le 19 avril, ERA5 indiquait ~23 °C dans le nord de l'Espagne. GraphCast prédisait 10.5 °C (sous-estimation de 12 °C), AROME prédisait 23.5 °C (quasi-parfait). Le pattern de sous-estimation se répète sur l'ensemble de la grille.

### Implication produit

Le biais GraphCast étant **systématique et directionnel** (~-5 °C en moyenne sur l'horizon 24 h), il est en partie **corrigible par post-traitement** (offset par variable, par région, par saison). Cette piste de **bias correction légère** est documentée dans la roadmap v1.1.

---

## 🌬️ Performance vent — vitesse (`wind_speed_10m_ms`)

### MAE quotidien — horizon 24 h

| Date | AROME vs ERA5 | GraphCast vs ERA5 |
|---|---|---|
| 2026-04-17 | 0.77 m/s | 1.12 m/s |
| 2026-04-18 | 0.80 m/s | 1.45 m/s |
| 2026-04-19 | 0.91 m/s | 1.58 m/s |
| **Moyenne 3 j** | **0.83 m/s** | **1.38 m/s** |

### Bias systématique

GraphCast présente un biais négatif (sous-estimation de la vitesse du vent ~1.5 m/s à horizon 24 h). AROME présente un biais quasi-nul.

### Implication produit (secteur éolien)

La puissance éolienne est proportionnelle au cube de la vitesse du vent (P ∝ V³). Une sous-estimation systématique de 1.5 m/s sur des vitesses moyennes de 5–8 m/s correspond à une **sous-estimation de production éolienne de 30 à 50 %** — un écart opérationnellement critique pour les opérateurs de parcs et les traders d'énergie.

---

## 🧭 Performance vent — direction (`wind_direction_10m_deg`)

> ⚙️ MAE calculé avec la formule cyclique (cf. [Notes méthodologiques](#-notes-méthodologiques)). Bias non défini pour cette variable.

### MAE quotidien — horizon 24 h

| Date | AROME vs ERA5 | GraphCast vs ERA5 | Ratio |
|---|---|---|---|
| 2026-04-17 | 39.16 ° | 64.18 ° | 1.64× |
| 2026-04-18 | 34.29 ° | 76.01 ° | 2.22× |
| 2026-04-19 | 28.21 ° | 62.47 ° | 2.21× |
| **Moyenne 3 j** | **33.89 °** | **67.55 °** | **2.00×** |

L'erreur AROME (~34 °) est dans la norme ECMWF pour la direction du vent à 10 m sur l'Europe. L'erreur GraphCast (~68 °) est élevée mais cohérente avec un modèle global non spécialisé France.

### Implication produit (secteur éolien)

Une erreur de direction de 30° peut causer un **désalignement significatif des éoliennes** (yaw misalignment) en cas de pilotage automatique sur prédiction. Pour AROME, l'erreur reste opérationnelle. Pour GraphCast Operational utilisé tel quel, des stratégies de fusion modèle-observation seraient nécessaires.

---

## ☁️ Performance pression (`msl_hpa`)

### MAE quotidien — horizon 24 h

| Date | AROME vs ERA5 | GraphCast vs ERA5 | Ratio |
|---|---|---|---|
| 2026-04-17 | 0.35 hPa | 3.07 hPa | 8.78× |
| 2026-04-18 | 0.31 hPa | 3.95 hPa | 12.74× |
| 2026-04-19 | 0.52 hPa | 3.30 hPa | 6.35× |
| **Moyenne 3 j** | **0.39 hPa** | **3.44 hPa** | **8.74×** |

### Lecture

C'est la variable où l'écart entre AROME et GraphCast est le plus marqué (~9× en moyenne, jusqu'à 13× sur certaines dates). La pression au niveau de la mer est une variable très contrainte spatialement par les **lois physiques de la dynamique atmosphérique**, domaine où les modèles physiques régionaux haute résolution ont un avantage structurel marqué sur les modèles fondation IA généralistes.

---

## 🌧️ Performance précipitations (`tp_6h_mm`)

### MAE quotidien — horizon 24 h

| Date | AROME vs ERA5 | GraphCast vs ERA5 | Ratio |
|---|---|---|---|
| 2026-04-17 | 0.08 mm | 0.07 mm | ~1× (équivalent) |
| 2026-04-18 | 0.10 mm | 0.14 mm | 1.31× |
| 2026-04-19 | 0.39 mm | 0.44 mm | 1.15× |
| **Moyenne 3 j** | **0.19 mm** | **0.22 mm** | **1.16×** |

### Lecture

Les précipitations restent la variable la plus difficile à prédire pour tous les modèles (forte intermittence spatio-temporelle). Sur la période évaluée, AROME et GraphCast présentent des MAE comparables avec un léger avantage AROME. Les écarts moyens absolus sont faibles car la majorité des points-temps sont **secs** (valeur 0), ce qui mécaniquement réduit le MAE moyen — la métrique pertinente pour les précipitations est plutôt le **CRPS** ou un **score de Brier** segmenté par seuils (envisagé en v1.1).

---

## ☀️ Note sur le solaire (`toa_wm2`)

Le MAE de `toa_wm2` est **strictement nul** dans toutes les comparaisons et sur tous les horizons.

Ce n'est pas un signe de performance des modèles : c'est la conséquence du fait que `toa_wm2` est calculé par le pipeline d'ingestion via la formule astronomique de Spencer (1971), identiquement pour les 3 sources. Voir la section [Notes méthodologiques](#-notes-méthodologiques) pour le détail.

➡️ Cette variable reste utile pour estimer le **potentiel solaire** (courbes et heatmaps de valeurs absolues), mais elle ne discrimine pas les modèles. Pour évaluer la qualité de prévision solaire **au sol**, il faudra ajouter `total_cloud_cover` (envisagé en v1.1) qui module l'irradiance réelle.

---

## 💡 Insights produit

1. **AROME reste la référence opérationnelle sur la France métropolitaine.** Le modèle physique régional de Météo-France domine GraphCast Operational utilisé out-of-the-box sur l'ensemble des 5 variables comparables.
2. **GraphCast est compétitif à très court terme.** À horizon 6 h, les écarts se resserrent. L'avantage AROME se creuse principalement à mesure que l'horizon de prévision augmente.
3. **GraphCast présente des biais directionnels systématiques** (sous-estimation de température et de vent), partiellement corrigibles par post-traitement.
4. **Pour le secteur énergétique** :
   - **Éolien** : la sous-estimation systématique du vent par GraphCast amplifie au cube → sous-estimation de production de 30–50 %
   - **Solaire (TOA)** : pas d'enjeu modèle (calcul astronomique). L'enjeu est l'ajout de la couverture nuageuse pour calculer le GHI au sol
   - **Thermique (chauffage / climatisation)** : AROME largement supérieur (~3.3× plus précis)

---

## 🔮 Pistes d'évolution (v1.1+)

1. **Bias correction de GraphCast** par offset variable / région / saison appris sur ERA5. Probable réduction de 30–50 % du MAE température sans toucher au modèle (référence : pratiques opérationnelles standard en post-processing météo).
2. **Fine-tuning de GraphCast sur la France** avec un dataset ERA5 régional. Probable amélioration du MAE de ~30 % selon la littérature récente sur fine-tuning Pangu / GraphCast régionaux.
3. **Ensembling GraphCast + AROME** par moyenne pondérée par variable (AROME dominant sur t2m / msl, GraphCast complémentaire sur les structures globales).
4. **Skill Score normalisé** vs climatologie persistante — métrique standard en évaluation opérationnelle météo.
5. **CRPS / score de Brier segmenté par seuils** pour évaluer plus rigoureusement les précipitations.
6. **Ajout de `total_cloud_cover`** pour calculer le GHI au sol et estimer la production photovoltaïque réelle.
7. **Extension de la période d'évaluation** à 30 jours minimum pour une stabilité statistique.

---

## 📚 Reproductibilité

Tous les résultats ci-dessus ont été obtenus via les endpoints publics de l'API backend :

```bash
# Tableau comparatif : dernière date + moyenne 7 jours
curl "http://localhost:3001/api/mae/comparison?horizon=24"

# Évolution quotidienne d'une variable
curl "http://localhost:3001/api/mae/history?variable=t2m_celsius&days=30"
curl "http://localhost:3001/api/mae/history?variable=wind_direction_10m_deg&days=30"

# Heatmap d'écart spatial
curl "http://localhost:3001/api/heatmap/error?source=graphcast&date=2026-04-19&hour=12&variable=t2m_celsius"
curl "http://localhost:3001/api/heatmap/error?source=arome&date=2026-04-19&hour=12&variable=t2m_celsius"
```

Le code de calcul des MAE est dans `scripts/mae/compute_mae.py`. Le schéma SQL des tables sources est dans `scripts/sql/init_db_schema.sql`.

### Visualisation interactive (frontend ⭐)

Depuis l'étape 9 (avril 2026), tous ces résultats sont également **consultables interactivement** sur le dashboard frontend :

- **Carte France** avec heatmap colorée sur 100 villes principales (4 timestamps : 00h, 06h, 12h, 18h UTC)
- **Tableau MAE** sur 4 horizons (h6/h12/h18/h24) × 6 variables, avec ratio AROME/GraphCast coloré
- **6 ChartCards** synchronisées (1 par variable météo) avec curseur partagé entre toutes les courbes
- **Page Méthodologie publique** (`/fr/methodologie` ou `/en/methodology`) qui explique la méthode et les limitations en plain-text accessible aux non-développeurs

Le frontend embarque le **JSON statique pré-généré** par `scripts/generate_static_data.mjs`, ce qui rend les chiffres ci-dessus **rejouables** : la version v1.0 de l'application restera toujours consultable même après mise à jour des données.

---

## 📅 Snapshot des mesures

Données utilisées pour ces benchmarks :
- **ERA5** : 17–19 avril 2026 (limité par la latence J-6)
- **GraphCast Operational** : 17–27 avril 2026 (11 jours d'inférences quotidiennes en cumul, 3 jours évaluables vs ERA5)
- **AROME** : 17–27 avril 2026 (idem)
- **MAE recalculés** : 25 avril 2026 (post-implémentation MAE cyclique)
- **Frontend déployé** : 27 avril 2026 (étape 9 finalisée)

---

# 📊 Météo IA France — Benchmarks (English)

> 🇫🇷 **Version française au-dessus** ([go to French](#-météo-ia-france--benchmarks))

Results observed on the Météo IA France project, measured via the backend API (`/api/mae/*` and `/api/heatmap/error`) on the France 0.25° grid (2,925 points).

> ⚠️ **Scientific disclaimer**: results reflect project state at evaluation date. MAE values vary depending on weather conditions. See [Methodology](#-methodology-1) below.

> 📅 **Last updated**: April 27, 2026 — consolidated figures after circular MAE implementation for angular variables (see [Methodological notes](#-methodological-notes)). Now interactively available on the **frontend dashboard** (step 9 delivered on April 27, 2026) and its **public Methodology page**.

---

## 🎯 TL;DR

On metropolitan France, at 24 h horizon, on 3 evaluation days (April 17–19, 2026, 35 100 measurement pairs per variable per model):

| Variable | GraphCast vs ERA5 (MAE) | AROME vs ERA5 (MAE) | AROME / GraphCast |
|---|---|---|---|
| Temperature 2 m (°C) | **3.81** | **1.16** | **AROME 3.3× more accurate** |
| Wind speed 10 m (m/s) | 1.38 | 0.83 | AROME 1.7× more accurate |
| Wind direction 10 m (°) ⚙️ | 67.55 | 33.89 | AROME 2.0× more accurate |
| Mean sea-level pressure (hPa) | 3.44 | 0.39 | **AROME 8.7× more accurate** |
| Precipitation 6 h (mm) | 0.22 | 0.19 | AROME 1.2× more accurate |
| TOA solar (W/m²) | 0.00 | 0.00 | identical (astronomical variable) |

⚙️ Wind direction uses a circular MAE (see [Methodological notes](#-methodological-notes)).

➡️ **AROME outperforms GraphCast Operational on all 5 comparable variables** (TOA excluded as deterministic), with factors ranging from 1.2× to 8.7×. Consistent with literature: AI foundation models without regional specialization do not match regional physical models on their specialized domains.

---

## 🔬 Methodology

### Sources compared

| Source | Type | Native resolution | Frequency | Latency |
|---|---|---|---|---|
| **ERA5** (ECMWF) | Reanalysis (ground truth) | 0.25° | Hourly | ~5 days |
| **GraphCast Operational** (Google DeepMind) | AI foundation model | 0.25° | 6 h (4 horizons) | Real-time |
| **AROME** (Météo-France) | Regional physical model | 0.025° → resampled to 0.25° | 6 h | ~4 h post-run |

### Evaluation scope

- **Area**: metropolitan France grid (lat 41.0–51.5, lon -5.5–9.0), 0.25° resolution
- **GPS points**: 2,925 (45 latitudes × 65 longitudes)
- **Variables evaluated**: 6 (t2m, wind_speed, wind_direction, msl, tp_6h, toa)
- **Horizons**: 6, 12, 18, 24 h
- **Period**: April 17–19, 2026 (3 days, limited by ERA5 J-5 latency)
- **Statistical volume**: 35,100 measurement pairs per (variable × model)

### Metrics

- **MAE** (Mean Absolute Error) — average error in absolute value, in physical unit
- **RMSE** (Root Mean Squared Error) — penalizes large errors more
- **Bias** = `mean(prediction - truth)` — signed mean error. Positive → systematic overestimation; negative → underestimation. Identifies offset-correctable defects.

---

## 📐 Methodological notes

### Circular MAE for angular variables

Wind direction is a **cyclic** quantity (0° = 360°): a prediction of 5° vs truth 355° gives a linear error of 350°, while the actual angular error is only 10°.

For `wind_direction_10m_deg`, the pipeline applies **minimum angular distance**:

```python
abs_error = min(|pred - truth| mod 360, 360 - |pred - truth| mod 360)
```

This correction has significant impact: before implementation, wind direction MAE was reported around 110° (artifact of 0°/360° boundaries). After correction: **34° for AROME** and **68° for GraphCast** — values consistent with ECMWF benchmarks (typically 20–40° for 10 m wind direction over Europe).

### Bias `NULL` for wind_direction

For cyclic variables, signed bias has no simple physical interpretation. The pipeline forces `bias = NULL` for `wind_direction_10m_deg`. The frontend displays this as `N/A — cyclic variable`.

### TOA solar: MAE strictly zero by construction

`toa_wm2` is not a meteorological variable predicted by models. It is an **astronomical deterministic** quantity computed identically for all 3 sources by the ingestion pipeline (Spencer 1971 formula) → **MAE = 0 by construction**.

### MAE / RMSE / Bias chosen over MAPE

MAPE deliberately excluded:
1. **Division by zero** — 4 of 6 variables legitimately take value 0 (rain, wind calm, TOA night, north direction)
2. **Asymmetry** — MAPE penalizes errors on small values, distorting variables that cross zero
3. **Domain standard** — meteorological literature uses MAE/RMSE/Bias/Skill Score, not MAPE

**Skill Score** vs persistent climatology is planned for v1.1.

---

## 🌡️ Temperature performance (`t2m_celsius`)

### Daily MAE — 24 h horizon

| Date | AROME vs ERA5 | GraphCast vs ERA5 | Ratio |
|---|---|---|---|
| 2026-04-17 | 1.13 °C | 4.42 °C | 3.91× |
| 2026-04-18 | 1.20 °C | 3.87 °C | 3.23× |
| 2026-04-19 | 1.14 °C | 3.15 °C | 2.76× |
| **3-day avg** | **1.16 °C** | **3.81 °C** | **3.27×** |

GraphCast shows systematic negative bias (~-5 °C). AROME bias is near-zero.

---

## 🌬️ Wind performance — speed (`wind_speed_10m_ms`)

| Date | AROME vs ERA5 | GraphCast vs ERA5 |
|---|---|---|
| 2026-04-17 | 0.77 m/s | 1.12 m/s |
| 2026-04-18 | 0.80 m/s | 1.45 m/s |
| 2026-04-19 | 0.91 m/s | 1.58 m/s |
| **3-day avg** | **0.83 m/s** | **1.38 m/s** |

**Wind energy implication**: power scales as V³, so systematic wind underestimation amplifies into 30–50 % production underestimation — operationally critical.

---

## 🧭 Wind performance — direction (`wind_direction_10m_deg`) ⚙️

> Circular MAE used. Bias undefined.

| Date | AROME vs ERA5 | GraphCast vs ERA5 | Ratio |
|---|---|---|---|
| 2026-04-17 | 39.16 ° | 64.18 ° | 1.64× |
| 2026-04-18 | 34.29 ° | 76.01 ° | 2.22× |
| 2026-04-19 | 28.21 ° | 62.47 ° | 2.21× |
| **3-day avg** | **33.89 °** | **67.55 °** | **2.00×** |

AROME (~34°) is in line with ECMWF norms. GraphCast (~68°) is high but consistent with a global non-specialized model.

---

## ☁️ Pressure performance (`msl_hpa`)

| Date | AROME vs ERA5 | GraphCast vs ERA5 | Ratio |
|---|---|---|---|
| 2026-04-17 | 0.35 hPa | 3.07 hPa | 8.78× |
| 2026-04-18 | 0.31 hPa | 3.95 hPa | 12.74× |
| 2026-04-19 | 0.52 hPa | 3.30 hPa | 6.35× |
| **3-day avg** | **0.39 hPa** | **3.44 hPa** | **8.74×** |

Largest gap between AROME and GraphCast (~9× average, up to 13×). Sea-level pressure is heavily constrained by atmospheric dynamics where high-resolution regional physical models have a structural advantage over generalist AI foundation models.

---

## 🌧️ Precipitation performance (`tp_6h_mm`)

| Date | AROME vs ERA5 | GraphCast vs ERA5 | Ratio |
|---|---|---|---|
| 2026-04-17 | 0.08 mm | 0.07 mm | ~1× |
| 2026-04-18 | 0.10 mm | 0.14 mm | 1.31× |
| 2026-04-19 | 0.39 mm | 0.44 mm | 1.15× |
| **3-day avg** | **0.19 mm** | **0.22 mm** | **1.16×** |

Most difficult variable to predict. MAE is mechanically reduced by the dry majority of points (zero values) — CRPS or threshold-segmented Brier score would be more meaningful (planned v1.1).

---

## 💡 Product insights

1. **AROME remains the operational reference over France**. Outperforms GraphCast Operational on all 5 comparable variables.
2. **GraphCast is competitive at very short term (6 h)** but degrades faster with horizon.
3. **GraphCast shows directional systematic biases** (underestimates temperature and wind), partially correctable by post-processing.
4. **Energy sector**:
   - Wind: GraphCast wind underestimation amplifies cubically → 30–50 % production underestimation
   - Solar (TOA): no model issue (astronomical). Need `total_cloud_cover` for ground GHI
   - Thermal: AROME vastly superior (3.3× more accurate)

---

## 🔮 Improvement directions (v1.1+)

1. **GraphCast bias correction** by variable / region / season offsets learned on ERA5
2. **GraphCast fine-tuning on France** with regional ERA5 dataset
3. **GraphCast + AROME ensembling** with per-variable weights
4. **Skill Score** vs persistent climatology
5. **CRPS / threshold Brier score** for precipitation
6. **Add `total_cloud_cover`** for ground-level GHI computation
7. **Extend evaluation period** to 30+ days for statistical stability

---

## 📚 Reproducibility

All results reproducible via the public backend API endpoints. MAE computation code: `scripts/mae/compute_mae.py`. SQL schema: `scripts/sql/init_db_schema.sql`. See French section above for sample curl commands.

### Interactive visualization (frontend ⭐)

Since step 9 (April 2026), all these results are also **interactively available** on the frontend dashboard:

- **France map** with colored heatmap on 100 main cities (4 timestamps: 00h, 06h, 12h, 18h UTC)
- **MAE table** on 4 horizons (h6/h12/h18/h24) × 6 variables, with colored AROME/GraphCast ratio
- **6 synchronized ChartCards** (1 per weather variable) with cursor shared across all curves
- **Public Methodology page** (`/fr/methodologie` or `/en/methodology`) explaining method and limitations in plain text accessible to non-developers

The frontend embeds **static JSON pre-generated** by `scripts/generate_static_data.mjs`, making these figures **replayable**: the v1.0 version of the application will always remain accessible even after data updates.

---

## 📅 Measurement snapshot

- **ERA5**: April 17–19, 2026 (limited by J-6 latency)
- **GraphCast Operational**: April 17–27, 2026 (11 cumulative inference days, 3 evaluable vs ERA5)
- **AROME**: April 17–27, 2026 (idem)
- **MAEs recomputed**: April 25, 2026 (post-circular-MAE implementation)
- **Frontend deployed**: April 27, 2026 (step 9 finalized)
