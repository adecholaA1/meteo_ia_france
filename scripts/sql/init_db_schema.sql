-- ═══════════════════════════════════════════════════════════════════════════
-- PROJET : Plateforme de Prévision Météo IA pour l'Énergie — France
-- ÉTAPE  : 7 — Schéma de base de données PostgreSQL + PostGIS
-- FICHIER: init_db_schema.sql
-- DATE   : 22 avril 2026
-- VERSION: 1.0 (MVP)
-- ═══════════════════════════════════════════════════════════════════════════
--
-- OBJECTIF
-- --------
-- Ce script initialise la base de données `meteo_ia_db` avec :
--   • 4 tables pour stocker les données météorologiques des 3 sources
--     + les métriques de performance des modèles
--   • 2 vues "fresh" pour exposer au frontend les prévisions les plus récentes
--   • Les index nécessaires (B-tree + PostGIS GIST) pour des requêtes rapides
--
-- CONVENTION TIMEZONE — CRITIQUE POUR LA COHÉRENCE
-- -------------------------------------------------
-- TOUS les timestamps en DB sont STRICTEMENT en UTC.
-- Les 3 sources externes (ERA5, AROME, GraphCast) sont nativement en UTC.
-- La conversion UTC → Europe/Paris (UTC+1 hiver, UTC+2 été) se fait
-- UNIQUEMENT au niveau du frontend React via une fonction utilitaire.
--
-- Exemples :
--   22/04/2026 18:00 UTC → 22/04/2026 20:00 heure locale Paris (été)
--   22/12/2026 18:00 UTC → 22/12/2026 19:00 heure locale Paris (hiver)
--
-- FORMAT DES DONNÉES — LONG
-- --------------------------
-- Les tables sont en format LONG (1 ligne = 1 point × 1 variable × 1 timestamp).
-- Ce format est conforme aux notes officielles de l'étape 7 et constitue le
-- standard en data engineering pour données temporelles multi-dimensionnelles.
--
-- VERSION MVP v1.0 — SIMPLIFICATIONS
-- -----------------------------------
-- Contraintes techniques : VPS OVH CPU only (pas de GPU)
-- → 1 run GraphCast/jour + 1 run AROME/jour (au lieu de 4)
-- → Horizon 24h (J+1) au lieu de 48h
-- → Variables de surface uniquement (3D prévu en v1.1)
-- Le schéma DB est cependant prêt pour v1.1 sans migration nécessaire
-- (colonnes run_timestamp et forecast_horizon_h déjà présentes).
-- ═══════════════════════════════════════════════════════════════════════════


-- ───────────────────────────────────────────────────────────────────────────
-- CONFIGURATION DE LA DATABASE
-- ───────────────────────────────────────────────────────────────────────────

-- Forcer UTC comme timezone par défaut pour toutes les sessions PostgreSQL
ALTER DATABASE meteo_ia_db SET timezone = 'UTC';

-- Vérifier que PostGIS est bien installé (normalement fait à l'étape 6)
CREATE EXTENSION IF NOT EXISTS postgis;


-- ═══════════════════════════════════════════════════════════════════════════
-- TABLE 1 : era5_truth
-- ───────────────────────────────────────────────────────────────────────────
-- Stocke les valeurs de RÉANALYSE ERA5 (vérité terrain publiée par ECMWF).
-- Pas de run_timestamp car ERA5 = observation passée, pas une prévision.
-- Latence publication : ~5 jours (J-5 disponible aujourd'hui).
-- Pas de temps natif : 1h. On sélectionne 00h, 06h, 12h, 18h UTC.
-- ═══════════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS era5_truth (
    id                  SERIAL PRIMARY KEY,
    timestamp           TIMESTAMP WITH TIME ZONE NOT NULL,  -- Date/heure de l'observation (UTC)
    variable_name       VARCHAR(50) NOT NULL,               -- Ex : 'temperature_2m'
    unit                VARCHAR(10),                        -- Ex : 'K', 'm/s', 'Pa'
    latitude            NUMERIC(9, 6) NOT NULL,             -- 41° à 52° N (France)
    longitude           NUMERIC(9, 6) NOT NULL,             -- -6° à +10° E (France)
    value               NUMERIC(10, 4) NOT NULL,            -- Valeur mesurée
    created_at          TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    -- Contrainte d'unicité pour garantir l'idempotence des ingestions
    CONSTRAINT era5_truth_unique UNIQUE (timestamp, variable_name, latitude, longitude)
);

COMMENT ON TABLE era5_truth IS
    'Vérité terrain ERA5 (ECMWF Copernicus). Valeurs instantanées en UTC.';


-- ═══════════════════════════════════════════════════════════════════════════
-- TABLE 2 : arome_forecasts
-- ───────────────────────────────────────────────────────────────────────────
-- Stocke les PRÉVISIONS du modèle AROME (Météo-France).
-- Chaque run (init_timestamp) produit plusieurs prévisions à différents
-- horizons (+6h, +12h, +18h, +24h en v1.0).
-- Pas de temps : 6h (on sélectionne dans les 48 échéances horaires AROME).
-- Runs/jour v1.0 : 1 (run 00h UTC). En v1.1 : 4 runs (00h, 06h, 12h, 18h UTC).
-- ═══════════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS arome_forecasts (
    id                  SERIAL PRIMARY KEY,
    run_timestamp       TIMESTAMP WITH TIME ZONE NOT NULL,  -- Init du run AROME (00h UTC en v1.0)
    forecast_horizon_h  INT NOT NULL,                       -- 6, 12, 18, 24
    timestamp           TIMESTAMP WITH TIME ZONE NOT NULL,  -- Validité = run + horizon
    variable_name       VARCHAR(50) NOT NULL,
    unit                VARCHAR(10),
    latitude            NUMERIC(9, 6) NOT NULL,
    longitude           NUMERIC(9, 6) NOT NULL,
    value               NUMERIC(10, 4) NOT NULL,
    created_at          TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    -- Contrainte d'unicité : 1 ligne par (run × validité × variable × point)
    -- Permet idempotence + logique de freshness (plusieurs runs pour même timestamp)
    CONSTRAINT arome_forecasts_unique UNIQUE
        (run_timestamp, timestamp, variable_name, latitude, longitude)
);

COMMENT ON TABLE arome_forecasts IS
    'Prévisions AROME (Météo-France). run_timestamp + forecast_horizon_h = timestamp.';


-- ═══════════════════════════════════════════════════════════════════════════
-- TABLE 3 : graphcast_predictions
-- ───────────────────────────────────────────────────────────────────────────
-- Stocke les PRÉVISIONS du modèle GraphCast (DeepMind).
-- Structure IDENTIQUE à arome_forecasts pour faciliter les comparaisons.
-- Pas de temps natif : 6h (contrainte architecturale du modèle).
-- Horizons v1.0 : +6h, +12h, +18h, +24h (4 horizons par run).
-- ═══════════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS graphcast_predictions (
    id                  SERIAL PRIMARY KEY,
    run_timestamp       TIMESTAMP WITH TIME ZONE NOT NULL,  -- Init de l'inférence GraphCast
    forecast_horizon_h  INT NOT NULL,                       -- 6, 12, 18, 24
    timestamp           TIMESTAMP WITH TIME ZONE NOT NULL,  -- Validité = run + horizon
    variable_name       VARCHAR(50) NOT NULL,
    unit                VARCHAR(10),
    latitude            NUMERIC(9, 6) NOT NULL,
    longitude           NUMERIC(9, 6) NOT NULL,
    value               NUMERIC(10, 4) NOT NULL,
    created_at          TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT graphcast_predictions_unique UNIQUE
        (run_timestamp, timestamp, variable_name, latitude, longitude)
);

COMMENT ON TABLE graphcast_predictions IS
    'Prévisions GraphCast (notre IA). Pas de temps natif 6h (contrainte modèle).';


-- ═══════════════════════════════════════════════════════════════════════════
-- TABLE 4 : mae_metrics
-- ───────────────────────────────────────────────────────────────────────────
-- Stocke les métriques de performance CALCULÉES (MAE, RMSE, biais).
-- 3 comparaisons possibles dans une SEULE table via la colonne `comparison` :
--   • 'graphcast_vs_era5'   → qualité de notre IA vs vérité terrain
--   • 'arome_vs_era5'       → qualité d'AROME vs vérité terrain
--   • 'graphcast_vs_arome'  → comparaison de notre IA vs Météo-France
-- Calculée quotidiennement par un script dédié (cron).
-- ═══════════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS mae_metrics (
    id                  SERIAL PRIMARY KEY,
    comparison          VARCHAR(30) NOT NULL,               -- Voir CHECK ci-dessous
    evaluation_date     DATE NOT NULL,                      -- Jour évalué
    variable_name       VARCHAR(50) NOT NULL,
    forecast_horizon_h  INT,                                -- NULL si toutes échéances confondues
    mae                 NUMERIC(10, 4) NOT NULL,            -- Erreur absolue moyenne
    rmse                NUMERIC(10, 4),                     -- Racine erreur quadratique moyenne
    bias                NUMERIC(10, 4),                     -- Biais systémique (+ ou -)
    sample_count        INT NOT NULL,                       -- Nb points utilisés
    computed_at         TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    -- Validation des valeurs autorisées pour comparison
    CONSTRAINT mae_metrics_comparison_check CHECK (
        comparison IN ('graphcast_vs_era5', 'arome_vs_era5', 'graphcast_vs_arome')
    ),

    -- Unicité : 1 métrique par (comparaison × jour × variable × horizon)
    CONSTRAINT mae_metrics_unique UNIQUE
        (comparison, evaluation_date, variable_name, forecast_horizon_h)
);

COMMENT ON TABLE mae_metrics IS
    'Métriques de performance calculées quotidiennement (MAE, RMSE, biais).';


-- ═══════════════════════════════════════════════════════════════════════════
-- INDEX — Performance des requêtes
-- ───────────────────────────────────────────────────────────────────────────
-- B-tree standard : filtrage rapide par timestamp, variable, horizon
-- PostGIS GIST   : requêtes spatiales (rayon autour d'un point, bounding box)
-- ═══════════════════════════════════════════════════════════════════════════

-- Index pour era5_truth
CREATE INDEX IF NOT EXISTS idx_era5_timestamp
    ON era5_truth (timestamp);
CREATE INDEX IF NOT EXISTS idx_era5_variable
    ON era5_truth (variable_name);
CREATE INDEX IF NOT EXISTS idx_era5_location
    ON era5_truth USING GIST (ST_Point(longitude, latitude));

-- Index pour arome_forecasts
CREATE INDEX IF NOT EXISTS idx_arome_timestamp_horizon
    ON arome_forecasts (timestamp, forecast_horizon_h);
CREATE INDEX IF NOT EXISTS idx_arome_run
    ON arome_forecasts (run_timestamp);
CREATE INDEX IF NOT EXISTS idx_arome_variable
    ON arome_forecasts (variable_name);
CREATE INDEX IF NOT EXISTS idx_arome_location
    ON arome_forecasts USING GIST (ST_Point(longitude, latitude));

-- Index pour graphcast_predictions
CREATE INDEX IF NOT EXISTS idx_graphcast_timestamp_horizon
    ON graphcast_predictions (timestamp, forecast_horizon_h);
CREATE INDEX IF NOT EXISTS idx_graphcast_run
    ON graphcast_predictions (run_timestamp);
CREATE INDEX IF NOT EXISTS idx_graphcast_variable
    ON graphcast_predictions (variable_name);
CREATE INDEX IF NOT EXISTS idx_graphcast_location
    ON graphcast_predictions USING GIST (ST_Point(longitude, latitude));

-- Index pour mae_metrics
CREATE INDEX IF NOT EXISTS idx_mae_date_comparison
    ON mae_metrics (evaluation_date, comparison);


-- ═══════════════════════════════════════════════════════════════════════════
-- VUES "FRESH" — Exposition au frontend
-- ───────────────────────────────────────────────────────────────────────────
-- Le frontend n'a pas besoin de TOUS les runs (ceux qui ont été "réchauffés").
-- Il veut uniquement la prévision la PLUS RÉCENTE pour chaque (timestamp, variable, point).
-- Les vues ci-dessous filtrent automatiquement via DISTINCT ON + ORDER BY.
-- Les données brutes restent en DB pour le calcul des MAE et l'analyse historique.
-- ═══════════════════════════════════════════════════════════════════════════

-- Vue : prévisions AROME "fraîches" (1 valeur par combinaison unique)
CREATE OR REPLACE VIEW arome_forecasts_fresh AS
SELECT DISTINCT ON (timestamp, variable_name, latitude, longitude)
    id,
    run_timestamp,
    forecast_horizon_h,
    timestamp,
    variable_name,
    unit,
    latitude,
    longitude,
    value,
    created_at
FROM arome_forecasts
ORDER BY timestamp, variable_name, latitude, longitude, run_timestamp DESC;

COMMENT ON VIEW arome_forecasts_fresh IS
    'Prévisions AROME les plus récentes pour chaque (timestamp, variable, point). Utilisée par le frontend.';

-- Vue : prévisions GraphCast "fraîches"
CREATE OR REPLACE VIEW graphcast_predictions_fresh AS
SELECT DISTINCT ON (timestamp, variable_name, latitude, longitude)
    id,
    run_timestamp,
    forecast_horizon_h,
    timestamp,
    variable_name,
    unit,
    latitude,
    longitude,
    value,
    created_at
FROM graphcast_predictions
ORDER BY timestamp, variable_name, latitude, longitude, run_timestamp DESC;

COMMENT ON VIEW graphcast_predictions_fresh IS
    'Prévisions GraphCast les plus récentes pour chaque (timestamp, variable, point). Utilisée par le frontend.';


-- ═══════════════════════════════════════════════════════════════════════════
-- FONCTION UTILITAIRE : utc_to_paris()
-- ───────────────────────────────────────────────────────────────────────────
-- Convertit un timestamp UTC en heure locale Paris (DST auto-géré par PostgreSQL).
-- Utile pour vérifications visuelles dans DBeaver.
-- Pas utilisée en production (la conversion se fait côté frontend React).
-- ═══════════════════════════════════════════════════════════════════════════

CREATE OR REPLACE FUNCTION utc_to_paris(ts TIMESTAMP WITH TIME ZONE)
RETURNS TIMESTAMP AS $$
    SELECT ts AT TIME ZONE 'Europe/Paris';
$$ LANGUAGE SQL IMMUTABLE;

COMMENT ON FUNCTION utc_to_paris IS
    'Helper pour tests manuels : convertit UTC → heure Paris (DST auto).';


-- ═══════════════════════════════════════════════════════════════════════════
-- REQUÊTES DE VALIDATION — À EXÉCUTER APRÈS CRÉATION
-- ───────────────────────────────────────────────────────────────────────────
-- Les requêtes suivantes sont des COMMENTAIRES. Copie-les une par une dans
-- DBeaver pour vérifier que tout est correctement créé.
-- ═══════════════════════════════════════════════════════════════════════════

-- 1. Lister les 4 tables créées
--    SELECT table_name FROM information_schema.tables
--    WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
--    ORDER BY table_name;

-- 2. Lister les 2 vues créées
--    SELECT table_name FROM information_schema.views
--    WHERE table_schema = 'public'
--    ORDER BY table_name;

-- 3. Vérifier les index
--    SELECT indexname, tablename FROM pg_indexes
--    WHERE schemaname = 'public'
--    ORDER BY tablename, indexname;

-- 4. Vérifier que PostGIS fonctionne
--    SELECT PostGIS_Version();

-- 5. Vérifier la timezone de la database
--    SHOW timezone;
--    -- Attendu : 'UTC' (au prochain rechargement de la session)

-- 6. Tester la fonction utc_to_paris
--    SELECT utc_to_paris('2026-04-22 18:00:00+00'::TIMESTAMPTZ);
--    -- Attendu en été : 2026-04-22 20:00:00 (UTC+2)

-- 7. Compter les lignes dans chaque table (toutes vides au départ)
--    SELECT 'era5_truth' AS table_name, COUNT(*) AS n FROM era5_truth
--    UNION ALL
--    SELECT 'arome_forecasts', COUNT(*) FROM arome_forecasts
--    UNION ALL
--    SELECT 'graphcast_predictions', COUNT(*) FROM graphcast_predictions
--    UNION ALL
--    SELECT 'mae_metrics', COUNT(*) FROM mae_metrics;


-- ═══════════════════════════════════════════════════════════════════════════
-- FIN DU SCRIPT init_db_schema.sql
-- ═══════════════════════════════════════════════════════════════════════════
