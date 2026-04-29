/**
 * ============================================================================
 *  📁 routes/heatmapRoutes.js
 * ----------------------------------------------------------------------------
 *  Routes liées aux heatmaps d'écart spatial (modèle vs vérité ERA5).
 *
 *  1 endpoint exposé :
 *    GET /api/heatmap/error  → grille d'écart (source - era5) pour 1 instant T
 *
 *  📚 Sources comparées :
 *     - graphcast (vue graphcast_predictions_fresh)  vs era5_truth
 *     - arome     (vue arome_forecasts_fresh)        vs era5_truth
 * ============================================================================
 */

const express = require('express');
const router = express.Router();
const heatmapController = require('../controllers/heatmapController');
const cache = require('../middleware/cache');

/**
 * GET /api/heatmap/error
 * Retourne la grille d'écart (source - era5) pour les 2925 points GPS
 * à un instant T donné, pour une source et une variable choisies.
 *
 * Query params :
 *   - source   : 'graphcast' | 'arome'  (défaut : 'graphcast')
 *   - date     : YYYY-MM-DD               (obligatoire)
 *   - hour     : 00 | 06 | 12 | 18        (obligatoire)
 *   - variable : nom de variable          (défaut : 't2m_celsius')
 *
 * Cache : 30 min (les données ne changent pas dans la journée)
 */
router.get(
  '/error',
  cache(1800),
  heatmapController.getError
);

module.exports = router;
