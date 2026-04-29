/**
 * ============================================================================
 *  📁 routes/forecastRoutes.js
 * ----------------------------------------------------------------------------
 *  Routes liées aux prévisions météo (GraphCast / AROME / ERA5).
 *
 *  4 endpoints exposés :
 *    1. GET /api/forecast/available-times  → dates + horizons disponibles
 *    2. GET /api/forecast/grid-points      → liste des 2925 points GPS
 *    3. GET /api/forecast/timeseries       → séries 7j × 6 vars × 1 point
 *    4. GET /api/forecast/:date/:hour      → grille complète à un instant T
 *
 *  + 1 endpoint admin (PHASE B.6) :
 *    5. POST /api/forecast/cache/clear     → vide le cache RAM (post-pipeline)
 *
 *  ⚠️ ORDRE IMPORTANT : les routes "fixes" (available-times, grid-points,
 *     timeseries, cache/clear) doivent être déclarées AVANT la route
 *     paramétrée /:date/:hour, sinon Express interprète "available-times"
 *     comme une date et plante.
 * ============================================================================
 */

const express = require('express');
const router = express.Router();
const forecastController = require('../controllers/forecastController');
const cache = require('../middleware/cache');

// 🟢 Routes fixes EN PREMIER (pour éviter les conflits avec :date/:hour)

/**
 * GET /api/forecast/available-times
 * Retourne la liste des dates + horizons disponibles pour une source donnée.
 * Query params :
 *   - source : 'graphcast' | 'arome' | 'era5'  (défaut : 'graphcast')
 *
 * 🆕 Cache : 1h (au lieu de 5 min)
 *    Justification : les nouvelles données arrivent 1×/jour via les pipelines.
 *    Le hook regenerate_frontend_json invalide le cache automatiquement après
 *    chaque ingestion → données toujours fraîches malgré le TTL long.
 */
router.get(
  '/available-times',
  cache(3600), // 1 heure (au lieu de 300 = 5 min)
  forecastController.getAvailableTimes
);

/**
 * GET /api/forecast/grid-points
 * Retourne les 2925 points GPS de la grille (lat/lon).
 * Cache : 1h (la grille ne change quasiment jamais)
 */
router.get(
  '/grid-points',
  cache(3600),
  forecastController.getGridPoints
);

/**
 * GET /api/forecast/timeseries
 * Retourne 7j de séries temporelles pour 1 point GPS, toutes variables, 3 sources.
 * Query params :
 *   - lat  : latitude  (défaut : 48.75 = Paris)
 *   - lon  : longitude (défaut : 2.5   = Paris)
 *   - days : nombre de jours d'historique (défaut : 7, max : 30)
 * Cache : 10 min (défaut)
 */
router.get(
  '/timeseries',
  cache(),
  forecastController.getTimeseries
);

// ═════════════════════════════════════════════════════════════════════════════
// 🆕 PHASE B.6 — Route admin pour invalider le cache après pipeline
// ═════════════════════════════════════════════════════════════════════════════

/**
 * POST /api/forecast/cache/clear
 * Vide ENTIÈREMENT le cache RAM (toutes routes confondues).
 *
 * Appelé automatiquement par le hook regenerate_frontend_json.py après
 * chaque ingestion réussie pour garantir des données toujours fraîches.
 *
 * Réponse :
 *   { "status": "ok", "message": "Cache vidé", "stats": { ... } }
 */
router.post('/cache/clear', (req, res) => {
  const statsBefore = cache.getStats();
  cache.flush();
  res.json({
    status: 'ok',
    message: 'Cache vidé entièrement',
    stats_before: statsBefore,
  });
});

// 🟡 Route paramétrée EN DERNIER

/**
 * GET /api/forecast/:date/:hour
 * Retourne la grille complète (2925 points) à un instant T pour 1 source.
 * Path params :
 *   - date : YYYY-MM-DD (ex: 2026-04-25)
 *   - hour : 00 | 06 | 12 | 18
 * Query params :
 *   - source   : 'graphcast' | 'arome' | 'era5'  (défaut : 'graphcast')
 *   - variable : nom de variable                  (défaut : 't2m_celsius')
 * Cache : 10 min (défaut)
 */
router.get(
  '/:date/:hour',
  cache(),
  forecastController.getForecastByDateHour
);

module.exports = router;
