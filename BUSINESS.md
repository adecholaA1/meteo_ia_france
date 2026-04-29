# 💼 Météo IA France — Business

> 🇬🇧 **English version below** ([jump to English](#-météo-ia-france--business-english))

[![Status](https://img.shields.io/badge/Statut-MVP_v1.0-blue.svg)]()
[![Marché](https://img.shields.io/badge/Marché-Énergie_FR-green.svg)]()
[![Modèle](https://img.shields.io/badge/Modèle-SaaS_B2B-orange.svg)]()
[![Licence](https://img.shields.io/badge/Coeur-Open_Source-red.svg)](LICENSE)

**Plateforme Deep Tech de comparaison de modèles de prévision météorologique pour le secteur de l'énergie.**

---

## 📑 Sommaire

1. [Pitch en 30 secondes](#-pitch-en-30-secondes)
2. [Le problème](#-le-problème)
3. [Notre solution](#-notre-solution)
4. [Marché cible](#-marché-cible)
5. [Différenciation concurrentielle](#-différenciation-concurrentielle)
6. [Modèle économique](#-modèle-économique)
7. [Traction et résultats](#-traction-et-résultats)
8. [Roadmap commerciale](#-roadmap-commerciale)
9. [Équipe et contact](#-équipe-et-contact)

---

## 🎯 Pitch en 30 secondes

Le secteur de l'énergie en France (éolien, solaire, trading) dépend critiquement de la qualité des prévisions météorologiques. Les opérateurs paient cher des fournisseurs commerciaux (Météo-France Pro, MeteoMatics, ClimaCell) sans pouvoir vérifier objectivement quel modèle leur donne les meilleurs résultats sur leur zone géographique. Avec l'arrivée des modèles IA fondation (GraphCast Google DeepMind, Pangu-Weather Huawei, ClimaX Microsoft), la question devient stratégique : ces nouvelles IA surpassent-elles vraiment les modèles physiques régionaux établis ?

**Météo IA France répond à cette question par la mesure**. Notre plateforme compare en continu sur la France métropolitaine (grille 0.25°, 2 925 points, 103 villes maillées) les prévisions de **GraphCast Operational** (IA Google DeepMind, GNN), **AROME** (Météo-France, modèle physique régional 1.3 km) et **ERA5** (ECMWF, vérité terrain de référence). Résultat : un dashboard transparent, bilingue, ouvert, qui démontre les écarts réels sur 6 variables critiques pour l'énergie (température, vent, pression, précipitations, rayonnement solaire).

---

## ❓ Le problème

### Pour les opérateurs énergétiques

Trois pain points concrets observés sur le marché français :

1. **Opacité des fournisseurs commerciaux** : Météo-France Pro, MeteoMatics, ClimaCell, Tomorrow.io facturent à l'API call ou à l'abonnement annuel sans publier de benchmarks indépendants par zone géographique ou par variable. Le client paie sans pouvoir comparer.

2. **Pas de standard de mesure objective** : chaque fournisseur publie ses propres scores favorables. Les benchmarks ECMWF officiels sont globaux et pondérés pour la météo synoptique, pas pour les usages énergie sur micro-zones (parc éolien Bretagne, ferme PV Provence).

3. **L'arrivée des IA fondation crée de la confusion stratégique** : faut-il acheter du GraphCast ? Du Pangu-Weather ? Garder du AROME ? Faire un mix ? Sans données comparatives transparentes, les directions opérationnelles décident à l'aveugle.

### Le coût caché

Une erreur de 1 m/s sur la prévision de vitesse de vent à 24 h sur un parc de 100 MW se traduit par une erreur de production de l'ordre de **15 à 30 MWh** sur la fenêtre considérée. Au prix spot moyen 2025 (~80 €/MWh), c'est entre **1 200 et 2 400 € par fenêtre par parc**. Cumulé sur 365 jours et plusieurs parcs, l'enjeu est en millions d'euros annuels.

---

## ✅ Notre solution

### Une plateforme de mesure indépendante

| Brique | Description | Statut |
|---|---|---|
| **Dashboard interactif** | Carte de France 103 villes + 6 graphiques séries temporelles synchronisés + tableau MAE par horizon | ✅ Production |
| **Pipelines automatisés** | 4 pipelines Python quotidiens (ERA5, AROME, GraphCast, MAE) avec retry, logs append-only, alertes | ✅ Production |
| **Backend API REST** | 9 endpoints Express avec cache 4 couches (latence <200 ms, p99 garantie) | ✅ Production |
| **Page Méthodologie publique** | 8 sections accessibles aux non-développeurs (glossaire, variables, sources, limitations) | ✅ Production |
| **Bilingue FR/EN natif** | Dashboard et documentation entièrement traduits, deux locales | ✅ Production |
| **API publique B2B** | Endpoints documentés OpenAPI, authentification clé API, plans freemium → enterprise | 🟡 v1.2 |
| **Alertes par zone** | Notifications email/Slack quand un modèle décroche significativement sur une zone donnée | 🟡 v2.0 |
| **Personnalisation client** | Variables custom, zones géographiques, horizons, pondération par critère métier | 🟡 v2.0 |

### Ce qui rend notre approche unique

1. **Code source ouvert sous licence MIT** : la communauté peut auditer la méthodologie, contribuer, forker. Pas de boîte noire commerciale.
2. **Vérité terrain ERA5** : référence ECMWF mondialement reconnue, pas un score interne propriétaire.
3. **MAE circulaire pour les variables angulaires** : implémentation rigoureuse pour `wind_direction_10m_deg`, conforme aux normes ECMWF (vs naïf 4× plus mauvais).
4. **Pattern hybride API runtime / JSON statique** : fallback gracieux, démonstration pédagogique en live possible (les recruteurs et décideurs voient le système fonctionner réellement).
5. **Latence sub-200 ms en p99** : grâce à l'indexation B-tree composite et au cache 4 couches (étape 11). Démontrable au curl en démo client.

---

## 🎯 Marché cible

### Cibles primaires (B2B SaaS)

| Segment | Profil | Volume FR | Pain point principal |
|---|---|---|---|
| **Opérateurs éoliens** | Gestionnaires de parcs (EDF Renouvelables, Engie Green, Boralex, RES) | ~30 acteurs majeurs | Optimisation production J+1 / J+3 |
| **Opérateurs solaires** | Développeurs et exploitants PV (Total Énergies, Voltalia, Neoen) | ~50 acteurs majeurs | Prévision GHI à 24-72h pour vente sur marché spot |
| **Traders énergie** | Salles de marché (RTE, EDF Trading, Engie Trading, indépendants) | ~20 desks | Arbitrage spot/forward sensible aux prévisions à courte échéance |
| **Aggregateurs / VPP** | Virtual Power Plants (Voltalis, Smart Grid Energy) | ~10 acteurs | Pilotage flexibilité demande sur fenêtres météo-sensibles |

### Cibles secondaires (B2B services)

- **Bureaux d'études énergie** (Tractebel, Artelia, Capgemini Invent practice énergie) : besoin de benchmarks indépendants pour conseiller leurs clients
- **Acteurs académiques** (CEA, CNRS, Sorbonne) : recherche reproductible sur la performance des modèles IA en météo
- **Régulateurs** (CRE, ADEME) : étude d'impact des nouveaux modèles IA sur la fiabilité du réseau

### Cibles tertiaires (B2C / pédagogiques)

- **Médias et journalistes data** : couvrir l'arrivée des IA fondation en météo avec un outil tangible
- **Étudiants et chercheurs** : ressource pédagogique open-source sur les NWP et l'IA en sciences environnementales

---

## 🆚 Différenciation concurrentielle

### Concurrents directs

| Acteur | Type | Forces | Faiblesses |
|---|---|---|---|
| **Météo-France Pro** | Fournisseur commercial historique | Modèle AROME natif, données HD, support 24/7 | Pas de benchmark IA, pas de transparence sur précision par zone |
| **MeteoMatics** (Suisse) | Agrégateur multi-modèles | API moderne, large catalogue, multi-cloud | Pricing élevé, opaque sur la qualité par modèle/zone |
| **ClimaCell / Tomorrow.io** (US) | Météo IA propriétaire | UX moderne, marketing fort | Modèle fermé, pas de comparaison avec les standards |
| **Open-Meteo** | API open-source gratuite | Gratuit, simple | Pas d'IA fondation, pas de comparaison, pas de UX dashboard |

### Notre positionnement

```
                              Transparence ↑
                                  │
                                  │
              Météo IA France ★   │
                                  │
                                  │
   Open-Meteo ●                   │
                                  │
                                  │ ● MeteoMatics
                                  │
─── Gratuit ──────────────────────┼──────────────────────── Payant ───
                                  │
                                  │
   Météo-France gratuit ●         │ ● Météo-France Pro
                                  │
                                  │ ● ClimaCell / Tomorrow.io
                                  │
                                  │
                                  ▼
                              Opacité
```

**Notre case** : transparence maximale (open-source) + données premium (vérité ERA5 + IA fondation), avec un modèle SaaS freemium pour les usages B2B avancés. Personne d'autre ne combine ces 4 dimensions.

---

## 💰 Modèle économique

### Stratégie : Open-Source Core + SaaS Premium

Le **cœur de la plateforme reste open-source MIT** (visibilité, contributions communautaires, validation académique). Les **features premium** (API quota élevés, alertes, personnalisation, support) sont monétisées en SaaS B2B.

### Plans tarifaires envisagés (v1.2 et au-delà)

| Plan | Prix | Cible | Features |
|---|---|---|---|
| **Free / Open** | Gratuit | Étudiants, journalistes, prototypes | Dashboard public, page Méthodologie, code source, données J-6 |
| **Starter** | 99 € / mois | Bureaux d'études, indépendants | API 10 000 req/mois, 1 zone géo, 5 variables, support email |
| **Pro** | 499 € / mois | Opérateurs éoliens/solaires < 500 MW | API 100 000 req/mois, 5 zones, 6 variables, alertes email |
| **Enterprise** | sur devis | Opérateurs > 500 MW, traders, agrégateurs | API illimité, multi-zones, SLA 99.9%, support dédié, custom benchmarks |

### Revenus complémentaires envisagés

- **Études custom** : benchmarks sur zones spécifiques pour clients enterprise (5-15 k€ par étude)
- **Formation** : ateliers "Comprendre les IA météo pour l'énergie" (B2B, 2-5 k€/jour)
- **Conseil intégration** : aide à l'intégration de l'API dans les SI clients (ESN classique, j/h)

### Coûts opérationnels estimés (mensuel, MVP)

| Poste | Coût |
|---|---|
| VPS OVH (Ubuntu 24, 8 GB RAM) | 25 € |
| Stockage NetCDF/CSV (200 GB SSD) | 10 € |
| API CDS Copernicus (ERA5) | gratuit (académique) |
| GFS NOMADS | gratuit |
| Domaine + Certbot | 15 € / an |
| Monitoring (Uptime Kuma self-hosted) | inclus |
| **Total** | **~40 € / mois** |

→ **Marge brute > 95 %** dès le premier client Starter. Modèle SaaS classique.

---

## 📈 Traction et résultats

### Métriques de qualité scientifique (avril 2026)

Sur la France métropolitaine, à horizon 24 h, sur 3 jours d'évaluation (17–19 avril 2026, **35 100 paires de mesures par variable et par modèle**) :

| Variable | GraphCast vs ERA5 (MAE) | AROME vs ERA5 (MAE) | Conclusion |
|---|---|---|---|
| Température 2 m | 3.81 °C | **1.16 °C** | AROME 3.3× meilleur |
| Vitesse vent 10 m | 1.38 m/s | **0.83 m/s** | AROME 1.7× meilleur |
| Direction vent 10 m | 67.55° | **33.89°** | AROME 2.0× meilleur |
| Pression mer | 3.44 hPa | **0.39 hPa** | AROME 8.7× meilleur |
| Précipitations 6 h | 0.22 mm | **0.19 mm** | AROME 1.2× meilleur |
| Rayonnement solaire TOA | 0.00 | 0.00 | identique (astronomique) |

**Insight commercial** : sur la France métropolitaine, à courte échéance (J+1), un modèle physique régional spécialisé bat un modèle IA généraliste sur 5/5 variables comparables. Ce résultat, bien que cohérent avec la littérature scientifique, n'est pas connu de la majorité des décideurs. **C'est la valeur que nous apportons : une preuve mesurable et reproductible.**

### Métriques de performance technique

| Métrique | Valeur | Conditions |
|---|---|---|
| Latence API p50 | ~5 ms | cache hit |
| Latence API p99 | <200 ms | cache miss + DB query |
| Disponibilité visée | 99.5 % | post-déploiement étape 12 |
| Volume DB | 654K lignes / table de prédictions | 6 mois d'historique |
| Pipelines quotidiens | 4 (ERA5, AROME, GraphCast, MAE) | exécution nocturne 03h–06h Paris |

### Validation marché (à venir)

- **v1.2 (Q3 2026)** : ouverture API publique avec plans Starter/Pro, objectif 5 clients payants en 6 mois
- **v2.0 (Q1 2027)** : signature 1 client Enterprise (opérateur > 500 MW), objectif chiffre d'affaires annuel 50 k€
- **v3.0 (Q4 2027)** : levée de fonds seed 500 k€ pour scaler équipe et infrastructure

---

## 🗺️ Roadmap commerciale

### Phase 1 — MVP technique (✅ terminée, étapes 1-11)
✅ Dashboard fonctionnel, pipelines automatisés, documentation complète, performance prod-ready.

### Phase 2 — Production hardening (🟡 en cours, étape 12)

**Sous-phase 2.A — Dockerisation locale (✅ terminée le 29/04/2026)**
- ✅ 3 Dockerfiles production-ready (backend ~60 Mo, frontend ~23 Mo, postgres officiel PostGIS)
- ✅ `docker-compose.yml` orchestrant 3 services + healthchecks + volume persistant
- ✅ Nginx du container frontend avec **reverse proxy `/api/*`** vers backend
- ✅ ~80 erreurs TypeScript pré-existantes corrigées (refactoring qualité)
- ✅ `.env.production.example` template documenté pour le VPS
- ✅ `.gitignore` enrichi (4,7 Ko) avec exception backup `.sql` pour Git LFS
- ✅ **Domaine `meteo-ia.fr` acheté** 
- ✅ Stack locale validée visuellement (dashboard fonctionne avec données réelles)

**Sous-phase 2.B — Déploiement VPS (🔜 en cours)**
- 🔜 Configuration Git LFS pour le dump 333 Mo
- 🔜 Push vers GitHub repo public `meteo_ia_france`
- 🔜 SSH VPS OVH + `git clone` + `docker compose up -d --build`
- 🔜 Configuration DNS chez OVH : record A `meteo-ia.fr` → IP VPS
- 🔜 Nginx **host** sur le VPS (séparé des containers) pour reverse proxy + multiplexage avec `ai-elec-conso.fr` (autre projet)
- 🔜 Certbot Let's Encrypt pour HTTPS automatique
- 🔜 Crontab UTC pour 4 pipelines Python quotidiens

**Sous-phase 2.C — Hardening (🔜 V1.1)**
- 🔜 Tests unitaires (Jest backend, Vitest frontend, pytest pipelines)
- 🔜 CI/CD GitHub Actions (build Docker auto, lint, typecheck, deploy)
- 🔜 Monitoring (logs centralisés, alertes Slack/email sur erreurs pipelines)
- 🔜 30+ jours d'observation production avant lancement commercial

### Phase 3 — Lancement commercial (Q3 2026)
- Authentification API + plans freemium
- Documentation OpenAPI publique
- Site web marketing dédié (`meteo-ia.fr` ✅ acheté en V1.0)
- Stratégie inbound : articles techniques sur LinkedIn / Medium, présence aux salons énergie (Pollutec, Énergie 2030)
- Démarchage ciblé : 50 contacts identifiés dans les top 30 opérateurs FR

### Phase 4 — Expansion produit (Q1 2027)
- Variables additionnelles (cloud cover total, vent à 100m pour parcs éoliens, GHI au sol)
- Intégration Pangu-Weather (Huawei) en plus de GraphCast
- Comparaisons modèle vs modèle (au-delà de modèle vs vérité)
- Alertes intelligentes par zone et par seuil

### Phase 5 — Internationalisation (Q4 2027)
- Extension à l'Allemagne, Espagne, Italie (marchés énergie similaires)
- Partenariats avec ECMWF / DWD / Météo-Suisse
- Levée de fonds seed pour scaler

---

## 👥 Équipe et contact

### Fondateur

**Adechola Emile Kouande** — Ingénieur IA FullStack, double compétence Deep Learning + énergie (Optimisation numérique)
- LinkedIn : [linkedin.com/in/kadechola](https://www.linkedin.com/in/kadechola)
- Email : kadechola@gmail.com
- GitHub : [github.com/kouande](https://github.com/kouande)
- Malt : [malt.fr/profile/adecholaemilekkouande](https://www.malt.fr/profile/adecholaemilekkouande)

### Recherche d'opportunités

Le projet est ouvert à :
- 🤝 **Partenariats commerciaux** : opérateurs énergie, ESN, bureaux d'études souhaitant tester la plateforme
- 💼 **Opportunités professionnelles** : poste Data Scientist Senior / Lead Data dans le secteur énergie
- 💰 **Investissement seed** : business angels intéressés par la Deep Tech française et la transition énergétique
- 🎓 **Collaborations académiques** : laboratoires météo / IA pour valider les benchmarks et co-publier

---

## 📜 Licence

Code source : **MIT License** (libre utilisation commerciale, attribution requise).
Données : ERA5 sous licence Copernicus, GFS domaine public, AROME sous licence Étalab 2.0.
Documentation : **CC BY 4.0**.

---

# 💼 Météo IA France — Business (English)

> 🇫🇷 **Version française au-dessus** ([retour au français](#-météo-ia-france--business))

[![Status](https://img.shields.io/badge/Status-MVP_v1.0-blue.svg)]()
[![Market](https://img.shields.io/badge/Market-Energy_FR-green.svg)]()
[![Model](https://img.shields.io/badge/Model-SaaS_B2B-orange.svg)]()
[![License](https://img.shields.io/badge/Core-Open_Source-red.svg)](LICENSE)

**Deep Tech platform for weather forecasting model comparison in the energy sector.**

---

## 📑 Table of contents

1. [30-second pitch](#-30-second-pitch)
2. [The problem](#-the-problem)
3. [Our solution](#-our-solution)
4. [Target market](#-target-market)
5. [Competitive differentiation](#-competitive-differentiation)
6. [Business model](#-business-model)
7. [Traction and results](#-traction-and-results)
8. [Commercial roadmap](#-commercial-roadmap)
9. [Team and contact](#-team-and-contact)

---

## 🎯 30-second pitch

The energy sector in France (wind, solar, trading) critically depends on the quality of weather forecasts. Operators pay heavily for commercial providers (Météo-France Pro, MeteoMatics, ClimaCell) without being able to objectively verify which model gives them the best results in their geographic area. With the arrival of foundation AI models (GraphCast Google DeepMind, Pangu-Weather Huawei, ClimaX Microsoft), the question becomes strategic: do these new AIs really outperform established regional physical models?

**Météo IA France answers this question through measurement**. Our platform continuously compares on metropolitan France (0.25° grid, 2,925 points, 103 cities meshed) the forecasts from **GraphCast Operational** (Google DeepMind AI, GNN), **AROME** (Météo-France, regional physical model 1.3 km) and **ERA5** (ECMWF, ground-truth reference). Result: a transparent, bilingual, open dashboard that demonstrates real differences across 6 critical variables for energy (temperature, wind, pressure, precipitation, solar radiation).

---

## ❓ The problem

### For energy operators

Three concrete pain points observed in the French market:

1. **Commercial provider opacity**: Météo-France Pro, MeteoMatics, ClimaCell, Tomorrow.io charge per API call or annual subscription without publishing independent benchmarks per geographic zone or per variable. The customer pays without being able to compare.

2. **No objective measurement standard**: each provider publishes their own favorable scores. Official ECMWF benchmarks are global and weighted for synoptic weather, not for energy use cases on micro-zones (Brittany wind farm, Provence PV plant).

3. **The arrival of foundation AIs creates strategic confusion**: should we buy GraphCast? Pangu-Weather? Keep AROME? Mix them? Without transparent comparative data, operations leadership decides blindly.

### The hidden cost

A 1 m/s error on 24h wind speed forecast for a 100 MW farm translates to a production error of **15 to 30 MWh** over the time window considered. At the 2025 average spot price (~€80/MWh), that's **€1,200 to €2,400 per window per farm**. Cumulated over 365 days and multiple farms, the stakes are in millions of euros annually.

---

## ✅ Our solution

### An independent measurement platform

| Brick | Description | Status |
|---|---|---|
| **Interactive dashboard** | France map 103 cities + 6 synchronized time-series charts + MAE table by horizon | ✅ Production |
| **Automated pipelines** | 4 daily Python pipelines (ERA5, AROME, GraphCast, MAE) with retry, append-only logs, alerts | ✅ Production |
| **Backend REST API** | 9 Express endpoints with 4-layer cache (latency <200ms, p99 guaranteed) | ✅ Production |
| **Public Methodology page** | 8 sections accessible to non-developers (glossary, variables, sources, limitations) | ✅ Production |
| **Native FR/EN bilingual** | Dashboard and documentation fully translated, two locales | ✅ Production |
| **B2B public API** | OpenAPI-documented endpoints, API key authentication, freemium → enterprise plans | 🟡 v1.2 |
| **Zone-based alerts** | Email/Slack notifications when a model significantly underperforms in a given zone | 🟡 v2.0 |
| **Customer customization** | Custom variables, geographic zones, horizons, business-criterion weighting | 🟡 v2.0 |

### What makes our approach unique

1. **Open-source code under MIT license**: the community can audit the methodology, contribute, fork. No commercial black box.
2. **ERA5 ground truth**: globally recognized ECMWF reference, not a proprietary internal score.
3. **Circular MAE for angular variables**: rigorous implementation for `wind_direction_10m_deg`, compliant with ECMWF norms (vs naive 4× worse).
4. **Hybrid API runtime / static JSON pattern**: graceful fallback, live pedagogical demonstration possible (recruiters and decision-makers see the system actually working).
5. **Sub-200ms latency at p99**: thanks to composite B-tree indexing and 4-layer cache (step 11). Demonstrable via curl in client demo.

---

## 🎯 Target market

### Primary targets (B2B SaaS)

| Segment | Profile | FR volume | Main pain point |
|---|---|---|---|
| **Wind operators** | Farm managers (EDF Renouvelables, Engie Green, Boralex, RES) | ~30 major players | D+1 / D+3 production optimization |
| **Solar operators** | PV developers and operators (Total Énergies, Voltalia, Neoen) | ~50 major players | 24-72h GHI forecast for spot market sale |
| **Energy traders** | Trading desks (RTE, EDF Trading, Engie Trading, independents) | ~20 desks | Spot/forward arbitrage sensitive to short-term forecasts |
| **Aggregators / VPP** | Virtual Power Plants (Voltalis, Smart Grid Energy) | ~10 players | Demand flexibility piloting on weather-sensitive windows |

### Secondary targets (B2B services)

- **Energy consulting firms** (Tractebel, Artelia, Capgemini Invent energy practice): need independent benchmarks to advise their clients
- **Academic actors** (CEA, CNRS, Sorbonne): reproducible research on AI model performance in weather
- **Regulators** (CRE, ADEME): impact study of new AI models on grid reliability

### Tertiary targets (B2C / pedagogical)

- **Media and data journalists**: cover the arrival of foundation AIs in weather with a tangible tool
- **Students and researchers**: open-source educational resource on NWP and AI in environmental sciences

---

## 🆚 Competitive differentiation

### Direct competitors

| Player | Type | Strengths | Weaknesses |
|---|---|---|---|
| **Météo-France Pro** | Historic commercial provider | Native AROME model, HD data, 24/7 support | No AI benchmark, no zone-precision transparency |
| **MeteoMatics** (Switzerland) | Multi-model aggregator | Modern API, large catalog, multi-cloud | High pricing, opaque on quality by model/zone |
| **ClimaCell / Tomorrow.io** (US) | Proprietary AI weather | Modern UX, strong marketing | Closed model, no comparison with standards |
| **Open-Meteo** | Free open-source API | Free, simple | No foundation AI, no comparison, no UX dashboard |

### Our positioning

```
                              Transparency ↑
                                  │
                                  │
              Météo IA France ★   │
                                  │
                                  │
   Open-Meteo ●                   │
                                  │
                                  │ ● MeteoMatics
                                  │
─── Free ─────────────────────────┼──────────────────────── Paid ────
                                  │
                                  │
   Météo-France free ●            │ ● Météo-France Pro
                                  │
                                  │ ● ClimaCell / Tomorrow.io
                                  │
                                  │
                                  ▼
                              Opacity
```

**Our slot**: maximum transparency (open-source) + premium data (ERA5 ground truth + foundation AI), with a freemium SaaS model for advanced B2B uses. No one else combines these 4 dimensions.

---

## 💰 Business model

### Strategy: Open-Source Core + Premium SaaS

The **platform core remains open-source MIT** (visibility, community contributions, academic validation). The **premium features** (high API quotas, alerts, customization, support) are monetized as B2B SaaS.

### Planned pricing tiers (v1.2 and beyond)

| Plan | Price | Target | Features |
|---|---|---|---|
| **Free / Open** | Free | Students, journalists, prototypes | Public dashboard, Methodology page, source code, J-6 data |
| **Starter** | €99 / month | Consulting firms, independents | API 10,000 req/month, 1 geo zone, 5 variables, email support |
| **Pro** | €499 / month | Wind/solar operators < 500 MW | API 100,000 req/month, 5 zones, 6 variables, email alerts |
| **Enterprise** | quote-based | Operators > 500 MW, traders, aggregators | Unlimited API, multi-zone, SLA 99.9%, dedicated support, custom benchmarks |

### Complementary revenue streams

- **Custom studies**: benchmarks on specific zones for enterprise customers (€5-15k per study)
- **Training**: workshops "Understanding weather AIs for energy" (B2B, €2-5k/day)
- **Integration consulting**: help integrating the API into customer IS (classic ESN, j/h)

### Estimated operational costs (monthly, MVP)

| Item | Cost |
|---|---|
| VPS OVH (Ubuntu 24, 8 GB RAM) | €25 |
| NetCDF/CSV storage (200 GB SSD) | €10 |
| Copernicus CDS API (ERA5) | free (academic) |
| GFS NOMADS | free |
| Domain + Certbot | €15 / year |
| Monitoring (self-hosted Uptime Kuma) | included |
| **Total** | **~€40 / month** |

→ **Gross margin > 95%** from the first Starter customer. Classic SaaS model.

---

## 📈 Traction and results

### Scientific quality metrics (April 2026)

On metropolitan France, at 24h horizon, over 3 days of evaluation (April 17–19, 2026, **35,100 measurement pairs per variable per model**):

| Variable | GraphCast vs ERA5 (MAE) | AROME vs ERA5 (MAE) | Conclusion |
|---|---|---|---|
| Temperature 2m | 3.81 °C | **1.16 °C** | AROME 3.3× better |
| Wind speed 10m | 1.38 m/s | **0.83 m/s** | AROME 1.7× better |
| Wind direction 10m | 67.55° | **33.89°** | AROME 2.0× better |
| Sea pressure | 3.44 hPa | **0.39 hPa** | AROME 8.7× better |
| Precipitation 6h | 0.22 mm | **0.19 mm** | AROME 1.2× better |
| TOA solar radiation | 0.00 | 0.00 | identical (astronomical) |

**Commercial insight**: on metropolitan France, at short range (D+1), a specialized regional physical model beats a generalist AI model on 5/5 comparable variables. This result, although consistent with scientific literature, is unknown to most decision-makers. **This is the value we bring: measurable and reproducible proof.**

### Technical performance metrics

| Metric | Value | Conditions |
|---|---|---|
| API latency p50 | ~5 ms | cache hit |
| API latency p99 | <200 ms | cache miss + DB query |
| Target availability | 99.5% | post-deployment step 12 |
| DB volume | 654K rows / prediction table | 6 months history |
| Daily pipelines | 4 (ERA5, AROME, GraphCast, MAE) | nightly run 03h–06h Paris |

### Market validation (upcoming)

- **v1.2 (Q3 2026)**: public API opening with Starter/Pro plans, target 5 paying customers in 6 months
- **v2.0 (Q1 2027)**: sign 1 Enterprise customer (operator > 500 MW), target annual revenue €50k
- **v3.0 (Q4 2027)**: seed fundraising €500k to scale team and infrastructure

---

## 🗺️ Commercial roadmap

### Phase 1 — Technical MVP (✅ completed, steps 1-11)
✅ Functional dashboard, automated pipelines, complete documentation, production-ready performance.

### Phase 2 — Production hardening (🟡 in progress, step 12)

**Sub-phase 2.A — Local dockerization (✅ completed on 04/29/2026)**
- ✅ 3 production-ready Dockerfiles (backend ~60 MB, frontend ~23 MB, official PostGIS postgres)
- ✅ `docker-compose.yml` orchestrating 3 services + healthchecks + persistent volume
- ✅ Frontend container's Nginx with **`/api/*` reverse proxy** to backend
- ✅ ~80 pre-existing TypeScript errors fixed (quality refactoring)
- ✅ `.env.production.example` template documented for VPS
- ✅ Enriched `.gitignore` (4.7 KB) with `.sql` backup exception for Git LFS
- ✅ **Domain `meteo-ia.fr` registered** 
- ✅ Local stack visually validated (dashboard works with real data)

**Sub-phase 2.B — VPS deployment (🔜 in progress)**
- 🔜 Git LFS configuration for the 333 MB dump
- 🔜 Push to public GitHub repo `meteo_ia_france`
- 🔜 SSH OVH VPS + `git clone` + `docker compose up -d --build`
- 🔜 DNS configuration at OVH: A record `meteo-ia.fr` → VPS IP
- 🔜 Host Nginx on VPS (separate from containers) for reverse proxy + multiplexing with `ai-elec-conso.fr` (other project)
- 🔜 Certbot Let's Encrypt for automatic HTTPS
- 🔜 UTC crontab for 4 daily Python pipelines

**Sub-phase 2.C — Hardening (🔜 V1.1)**
- 🔜 Unit tests (Jest backend, Vitest frontend, pytest pipelines)
- 🔜 GitHub Actions CI/CD (auto Docker build, lint, typecheck, deploy)
- 🔜 Monitoring (centralized logs, Slack/email alerts on pipeline errors)
- 🔜 30+ days of production observation before commercial launch

### Phase 3 — Commercial launch (Q3 2026)
- API authentication + freemium plans
- Public OpenAPI documentation
- Dedicated marketing website (`meteo-ia.fr` ✅ registered in V1.0)
- Inbound strategy: technical articles on LinkedIn / Medium, presence at energy conferences (Pollutec, Energy 2030)
- Targeted outreach: 50 contacts identified in the top 30 FR operators

### Phase 4 — Product expansion (Q1 2027)
- Additional variables (total cloud cover, wind at 100m for wind farms, surface GHI)
- Pangu-Weather (Huawei) integration in addition to GraphCast
- Model vs model comparisons (beyond model vs ground truth)
- Smart alerts by zone and threshold

### Phase 5 — Internationalization (Q4 2027)
- Extension to Germany, Spain, Italy (similar energy markets)
- Partnerships with ECMWF / DWD / MeteoSwiss
- Seed fundraising to scale

---

## 👥 Team and contact

### Founder

**Adechola Emile Kouande** — FullStack AI Engineer, dual Deep Learning + energy expertise (Numerical Optimization)
- LinkedIn: [linkedin.com/in/kadechola](https://www.linkedin.com/in/kadechola)
- Email: kadechola@gmail.com
- GitHub: [github.com/kouande](https://github.com/kouande)
- Malt: [malt.fr/profile/adecholaemilekkouande](https://www.malt.fr/profile/adecholaemilekkouande)

### Looking for opportunities

The project is open to:
- 🤝 **Commercial partnerships**: energy operators, ESNs, consulting firms wishing to test the platform
- 💼 **Professional opportunities**: Senior Data Scientist / Lead Data position in the energy sector
- 💰 **Seed investment**: business angels interested in French Deep Tech and energy transition
- 🎓 **Academic collaborations**: weather / AI labs to validate benchmarks and co-publish

---

## 📜 License

Source code: **MIT License** (free commercial use, attribution required).
Data: ERA5 under Copernicus license, GFS public domain, AROME under Étalab 2.0 license.
Documentation: **CC BY 4.0**.
