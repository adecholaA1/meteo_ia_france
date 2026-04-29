/**
 * ============================================================================
 *  📁 controllers/maeController.js
 * ----------------------------------------------------------------------------
 *  Logique métier pour les routes /api/mae/*
 *
 *  📚 Table source : mae_metrics
 *     Colonnes utiles : comparison, evaluation_date, variable_name,
 *                       forecast_horizon_h, mae, rmse, bias, sample_count
 *
 *  ⚠️ Bug timezone connu :
 *     evaluation_date est de type DATE. Quand pg sérialise, il l'envoie
 *     en TIMESTAMP avec timezone (ex: "2026-04-18T22:00:00.000Z" pour le
 *     19/04 interprété en Europe/Paris). On force le formatage YYYY-MM-DD
 *     côté SQL avec TO_CHAR pour éviter toute confusion.
 * ============================================================================
 */

const { pool } = require('../config/db');

// ----------------------------------------------------------------------------
// 🔧 CONSTANTES
// ----------------------------------------------------------------------------

const ALLOWED_VARIABLES = [
  't2m_celsius',
  'wind_speed_10m_ms',
  'wind_direction_10m_deg',
  'msl_hpa',
  'tp_6h_mm',
  'toa_wm2',
];

const COMPARISONS = [
  'graphcast_vs_era5',
  'graphcast_vs_arome',
  'arome_vs_era5',
];

const DEFAULT_HORIZON = 24;

// ----------------------------------------------------------------------------
// 🛠️ HELPERS
// ----------------------------------------------------------------------------

function validateVariable(variable) {
  if (!ALLOWED_VARIABLES.includes(variable)) {
    const err = new Error(
      `Variable invalide : "${variable}". Valeurs autorisées : ${ALLOWED_VARIABLES.join(
        ', '
      )}`
    );
    err.status = 400;
    throw err;
  }
}

// ============================================================================
//  1️⃣  GET /api/mae/comparison
// ============================================================================

/**
 * Pour chaque (comparaison, variable) : renvoie le MAE de la date la plus
 * récente ET la moyenne sur les 7 derniers jours.
 *
 * Format de réponse :
 * {
 *   "horizon": 24,
 *   "latest_date": "2026-04-18",
 *   "comparisons": {
 *     "graphcast_vs_era5": {
 *       "t2m_celsius":      { "latest": 4.42, "avg_7d": 3.85, "rmse_latest": 5.21, "bias_latest": -0.34 },
 *       "wind_speed_10m_ms":{ "latest": 1.23, "avg_7d": 1.45, ... },
 *       ...
 *     },
 *     "graphcast_vs_arome": { ... },
 *     "arome_vs_era5":      { ... }
 *   }
 * }
 *
 * Le frontend peut alors construire son tableau "AROME meilleur sur 5/6 vars"
 * en comparant les MAE de graphcast_vs_era5 vs arome_vs_era5.
 */
exports.getComparison = async (req, res, next) => {
  try {
    const horizon = parseInt(req.query.horizon, 10) || DEFAULT_HORIZON;

    // 🎯 Une seule requête SQL avec :
    //   - latest_date : la date la plus récente PAR (comparison, variable)
    //   - avg_7d      : la moyenne du MAE sur 7 jours glissants
    //   - latest_mae  : le MAE à latest_date (jointure self)
    //
    // On utilise un format YYYY-MM-DD propre via TO_CHAR pour éviter le bug
    // timezone qui transforme la date en "2026-04-18T22:00:00Z".
    const sql = `
      WITH ranked AS (
        SELECT
          comparison,
          variable_name,
          evaluation_date,
          mae::float  AS mae,
          rmse::float AS rmse,
          bias::float AS bias,
          ROW_NUMBER() OVER (
            PARTITION BY comparison, variable_name
            ORDER BY evaluation_date DESC
          ) AS rn
        FROM mae_metrics
        WHERE forecast_horizon_h = $1
          AND variable_name = ANY($2::text[])
      ),
      latest AS (
        SELECT comparison, variable_name, evaluation_date, mae, rmse, bias
        FROM ranked
        WHERE rn = 1
      ),
      avg7 AS (
        SELECT
          comparison,
          variable_name,
          AVG(mae)::float AS avg_7d
        FROM mae_metrics
        WHERE forecast_horizon_h = $1
          AND variable_name = ANY($2::text[])
          AND evaluation_date >= (
            SELECT MAX(evaluation_date) FROM mae_metrics
            WHERE forecast_horizon_h = $1
          ) - INTERVAL '6 days'
        GROUP BY comparison, variable_name
      )
      SELECT
        l.comparison,
        l.variable_name,
        TO_CHAR(l.evaluation_date, 'YYYY-MM-DD') AS evaluation_date,
        l.mae    AS latest_mae,
        l.rmse   AS latest_rmse,
        l.bias   AS latest_bias,
        a.avg_7d
      FROM latest l
      LEFT JOIN avg7 a
        ON a.comparison = l.comparison
       AND a.variable_name = l.variable_name
      ORDER BY l.comparison, l.variable_name
    `;

    const result = await pool.query(sql, [horizon, ALLOWED_VARIABLES]);

    if (result.rows.length === 0) {
      return res.status(404).json({
        status: 'not_found',
        message: `Aucune donnée MAE pour horizon=${horizon}h`,
        hint: 'Lance le pipeline MAE pour générer les métriques',
      });
    }

    // 🔄 Pivot : on regroupe par comparaison puis par variable
    const comparisons = {};
    for (const c of COMPARISONS) comparisons[c] = {};

    let latestDate = null;
    for (const row of result.rows) {
      if (!comparisons[row.comparison]) comparisons[row.comparison] = {};
      comparisons[row.comparison][row.variable_name] = {
        latest: row.latest_mae,
        avg_7d: row.avg_7d,
        rmse_latest: row.latest_rmse,
        bias_latest: row.latest_bias,
      };
      // Toutes les latest_date doivent être identiques mais on prend la max
      if (!latestDate || row.evaluation_date > latestDate) {
        latestDate = row.evaluation_date;
      }
    }

    res.json({
      horizon,
      latest_date: latestDate,
      comparisons,
    });
  } catch (err) {
    next(err);
  }
};

// ============================================================================
//  2️⃣  GET /api/mae/history
// ============================================================================

/**
 * Évolution quotidienne du MAE pour 1 variable, toutes comparaisons.
 *
 * Format de réponse (optimisé Recharts) :
 * {
 *   "variable": "t2m_celsius",
 *   "horizon": 24,
 *   "days": 30,
 *   "history": [
 *     { "date": "2026-04-12", "graphcast_vs_era5": 3.85, "graphcast_vs_arome": 2.10, "arome_vs_era5": 1.95 },
 *     { "date": "2026-04-13", "graphcast_vs_era5": 4.21, ... },
 *     ...
 *   ]
 * }
 */
exports.getHistory = async (req, res, next) => {
  try {
    const variable = req.query.variable || 't2m_celsius';
    validateVariable(variable);

    const horizon = parseInt(req.query.horizon, 10) || DEFAULT_HORIZON;
    const days = Math.min(parseInt(req.query.days, 10) || 30, 90);

    const sql = `
      SELECT
        TO_CHAR(evaluation_date, 'YYYY-MM-DD') AS date,
        comparison,
        mae::float AS mae
      FROM mae_metrics
      WHERE variable_name = $1
        AND forecast_horizon_h = $2
        AND evaluation_date >= CURRENT_DATE - ($3 || ' days')::interval
      ORDER BY evaluation_date, comparison
    `;

    const result = await pool.query(sql, [variable, horizon, days]);

    // 🔄 Pivot : on regroupe par date et on étale les comparaisons en colonnes
    const byDate = new Map();
    for (const row of result.rows) {
      if (!byDate.has(row.date)) {
        byDate.set(row.date, { date: row.date });
      }
      byDate.get(row.date)[row.comparison] = row.mae;
    }

    res.json({
      variable,
      horizon,
      days,
      history: Array.from(byDate.values()),
    });
  } catch (err) {
    next(err);
  }
};
