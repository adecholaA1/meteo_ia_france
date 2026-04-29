// ═══════════════════════════════════════════════════════════════════════════
// Météo IA France — Backend
// controllers/healthController.js — Logique des endpoints monitoring
// ─────────────────────────────────────────────────────────────────────────────
// 2 fonctions exportées :
//   - getHealth : ping basique de la DB
//   - getStatus : métriques détaillées (counts + dernières dates + cache)
// ═══════════════════════════════════════════════════════════════════════════

const { query } = require('../config/db');
const cache = require('../middleware/cache');


// ─── GET /api/health ─────────────────────────────────────────────────────────
// Vérifie que la DB répond avec un SELECT 1 (ultra rapide).
// Réponse :
//   200 OK : { status: 'ok', timestamp, uptime_seconds }
//   503 Service Unavailable : { status: 'error', message }
async function getHealth(req, res, next) {
  try {
    // SELECT 1 = la requête la plus rapide possible (juste pour voir si la DB répond)
    await query('SELECT 1');

    res.status(200).json({
      status: 'ok',
      message: 'API et DB opérationnelles',
      timestamp: new Date().toISOString(),
      uptime_seconds: Math.floor(process.uptime()),
    });
  } catch (err) {
    // En cas d'échec DB, on renvoie 503 (Service Unavailable)
    res.status(503).json({
      status: 'error',
      message: 'La DB ne répond pas',
      timestamp: new Date().toISOString(),
    });
  }
}


// ─── GET /api/status ─────────────────────────────────────────────────────────
// Métriques détaillées :
//   - counts par table (graphcast, arome, era5, mae)
//   - dernières dates ingérées (pour savoir si les pipelines tournent bien)
//   - stats du cache RAM
//
// Réponse :
//   {
//     tables: {
//       graphcast_predictions: { count, latest_run, latest_timestamp },
//       arome_forecasts:       { count, latest_run, latest_timestamp },
//       era5_truth:            { count, latest_timestamp },
//       mae_metrics:           { count, latest_evaluation_date }
//     },
//     cache: { keys, hits, misses, hitRate, ttl_seconds },
//     server: { uptime_seconds, node_env }
//   }
async function getStatus(req, res, next) {
  try {
    // ─── Requêtes parallèles pour aller plus vite ─────────────────────────
    // Au lieu d'attendre chaque requête une par une, on les lance en parallèle
    // avec Promise.all → ~80ms au lieu de ~400ms
    const [
      graphcastResult,
      aromeResult,
      era5Result,
      maeResult,
    ] = await Promise.all([
      // GraphCast : count + dernier run + dernier timestamp
      query(`
        SELECT
          COUNT(*) AS count,
          MAX(run_timestamp) AS latest_run,
          MAX(timestamp) AS latest_timestamp
        FROM graphcast_predictions
      `),
      // AROME : count + dernier run + dernier timestamp
      query(`
        SELECT
          COUNT(*) AS count,
          MAX(run_timestamp) AS latest_run,
          MAX(timestamp) AS latest_timestamp
        FROM arome_forecasts
      `),
      // ERA5 : count + dernier timestamp (pas de run_timestamp dans ce schéma)
      query(`
        SELECT
          COUNT(*) AS count,
          MAX(timestamp) AS latest_timestamp
        FROM era5_truth
      `),
      // MAE : count + dernière date d'évaluation
      query(`
        SELECT
          COUNT(*) AS count,
          MAX(evaluation_date) AS latest_evaluation_date
        FROM mae_metrics
      `),
    ]);


    // ─── Construction de la réponse ─────────────────────────────────────────
    res.status(200).json({
      tables: {
        graphcast_predictions: {
          count: parseInt(graphcastResult.rows[0].count, 10),
          latest_run: graphcastResult.rows[0].latest_run,
          latest_timestamp: graphcastResult.rows[0].latest_timestamp,
        },
        arome_forecasts: {
          count: parseInt(aromeResult.rows[0].count, 10),
          latest_run: aromeResult.rows[0].latest_run,
          latest_timestamp: aromeResult.rows[0].latest_timestamp,
        },
        era5_truth: {
          count: parseInt(era5Result.rows[0].count, 10),
          latest_timestamp: era5Result.rows[0].latest_timestamp,
        },
        mae_metrics: {
          count: parseInt(maeResult.rows[0].count, 10),
          latest_evaluation_date: maeResult.rows[0].latest_evaluation_date,
        },
      },
      cache: cache.getStats(),
      server: {
        uptime_seconds: Math.floor(process.uptime()),
        node_env: process.env.NODE_ENV || 'development',
        timestamp: new Date().toISOString(),
      },
    });
  } catch (err) {
    // Les erreurs DB sont déléguées au errorHandler centralisé
    next(err);
  }
}


// ─── Exports ─────────────────────────────────────────────────────────────────
module.exports = {
  getHealth,
  getStatus,
};
