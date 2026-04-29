/**
 * ============================================================================
 *  📁 routes/maeRoutes.js
 * ----------------------------------------------------------------------------
 *  Routes liées aux métriques MAE (Mean Absolute Error).
 *
 *  2 endpoints exposés :
 *    1. GET /api/mae/comparison  → tableau MAE (dernière date + moyenne 7j)
 *    2. GET /api/mae/history     → évolution quotidienne du MAE (graph)
 *
 *  📚 Source de données : table `mae_metrics` (colonne `comparison`) :
 *     - 'graphcast_vs_era5'
 *     - 'graphcast_vs_arome'
 *     - 'arome_vs_era5'
 * ============================================================================
 */

const express = require('express');
const router = express.Router();
const maeController = require('../controllers/maeController');
const cache = require('../middleware/cache');

/**
 * GET /api/mae/comparison
 * Tableau récapitulatif : pour chaque variable, MAE à la date la plus récente
 * + moyenne sur les 7 derniers jours, pour les 3 comparaisons.
 *
 * Query params :
 *   - horizon : forecast_horizon_h à filtrer (défaut : 24)
 *
 * Cache : 30 min (les MAE sont calculés 1×/jour)
 */
router.get(
  '/comparison',
  cache(1800),
  maeController.getComparison
);

/**
 * GET /api/mae/history
 * Évolution quotidienne du MAE pour 1 variable, toutes comparaisons.
 *
 * Query params :
 *   - variable : nom de variable (défaut : 't2m_celsius')
 *   - horizon  : forecast_horizon_h à filtrer (défaut : 24)
 *   - days     : nombre de jours d'historique (défaut : 30, max : 90)
 *
 * Cache : 30 min
 */
router.get(
  '/history',
  cache(1800),
  maeController.getHistory
);

module.exports = router;
