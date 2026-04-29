/**
 * ============================================================================
 *  📁 controllers/heatmapController.js
 * ----------------------------------------------------------------------------
 *  Logique métier pour les routes /api/heatmap/*
 *
 *  📚 Sources interrogées :
 *     - graphcast_predictions_fresh  (vue : 1 ligne par tuple, run le + récent)
 *     - arome_forecasts_fresh        (vue : idem)
 *     - era5_truth                   (table directe = vérité terrain)
 *
 *  🎯 Calcul : error = source.value - era5.value
 *     → error positif = source SUR-estime
 *     → error négatif = source SOUS-estime
 *     → error proche de 0 = bonne prédiction
 * ============================================================================
 */

const { pool } = require('../config/db');

// ----------------------------------------------------------------------------
// 🔧 CONSTANTES
// ----------------------------------------------------------------------------

// Seules graphcast et arome peuvent être comparées à era5 (era5 = vérité)
const SOURCE_TO_TABLE = {
  graphcast: 'graphcast_predictions_fresh',
  arome: 'arome_forecasts_fresh',
};

const ALLOWED_VARIABLES = [
  't2m_celsius',
  'wind_speed_10m_ms',
  'wind_direction_10m_deg',
  'msl_hpa',
  'tp_6h_mm',
  'toa_wm2',
];

// ----------------------------------------------------------------------------
// 🛠️ HELPERS
// ----------------------------------------------------------------------------

function resolveSource(sourceParam) {
  const source = (sourceParam || 'graphcast').toLowerCase();
  const table = SOURCE_TO_TABLE[source];
  if (!table) {
    const err = new Error(
      `Source invalide : "${source}". Valeurs autorisées pour la heatmap : ${Object.keys(
        SOURCE_TO_TABLE
      ).join(', ')} (era5 est la vérité, pas comparable à elle-même)`
    );
    err.status = 400;
    throw err;
  }
  return { source, table };
}

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
//  GET /api/heatmap/error
// ============================================================================

/**
 * Retourne l'écart (source - era5) sur la grille des 2925 points GPS,
 * pour 1 instant T, 1 source, 1 variable.
 *
 * Format de réponse :
 * {
 *   "source": "graphcast",
 *   "comparison": "graphcast - era5",
 *   "variable": "t2m_celsius",
 *   "timestamp": "2026-04-19T12:00:00Z",
 *   "count": 2925,
 *   "stats": {
 *     "min": -12.4,
 *     "max":  +3.1,
 *     "mean": -5.4,
 *     "abs_mean": 5.7    // = MAE spatial
 *   },
 *   "grid": [
 *     { "lat": 41.0, "lon": -6.0, "error": -8.4, "source_value": 5.2, "era5_value": 13.6 },
 *     ...
 *   ]
 * }
 *
 * ⚠️ Note pédagogique : on renvoie aussi source_value et era5_value pour
 *    permettre au frontend d'afficher un tooltip riche au survol d'un point
 *    ("GraphCast : 5.2°C / ERA5 : 13.6°C / Écart : -8.4°C").
 */
exports.getError = async (req, res, next) => {
  try {
    const { source, table } = resolveSource(req.query.source);
    const variable = req.query.variable || 't2m_celsius';
    validateVariable(variable);

    const { date, hour } = req.query;

    // Validation des params obligatoires
    if (!date || !hour) {
      const err = new Error(
        "Paramètres 'date' (YYYY-MM-DD) et 'hour' (00|06|12|18) obligatoires"
      );
      err.status = 400;
      throw err;
    }
    if (!/^\d{4}-\d{2}-\d{2}$/.test(date)) {
      const err = new Error(
        `Format date invalide : "${date}". Attendu : YYYY-MM-DD`
      );
      err.status = 400;
      throw err;
    }
    if (!/^(00|06|12|18)$/.test(hour)) {
      const err = new Error(
        `Heure invalide : "${hour}". Valeurs autorisées : 00, 06, 12, 18`
      );
      err.status = 400;
      throw err;
    }

    const targetTimestamp = `${date} ${hour}:00:00+00`;

    // 🎯 INNER JOIN sur (latitude, longitude) entre la source et era5_truth
    // pour le timestamp et la variable choisis.
    // → Si era5 est manquant pour ce timestamp (latence J-5), on retourne 404
    //   plutôt qu'une heatmap incomplète.
    const sql = `
      SELECT
        s.latitude::float  AS lat,
        s.longitude::float AS lon,
        s.value::float     AS source_value,
        e.value::float     AS era5_value,
        (s.value - e.value)::float AS error
      FROM ${table} s
      INNER JOIN era5_truth e
        ON  e.latitude  = s.latitude
        AND e.longitude = s.longitude
        AND e.timestamp = s.timestamp
        AND e.variable_name = s.variable_name
      WHERE s.timestamp = $1::timestamptz
        AND s.variable_name = $2
      ORDER BY lat, lon
    `;

    const result = await pool.query(sql, [targetTimestamp, variable]);

    if (result.rows.length === 0) {
      return res.status(404).json({
        status: 'not_found',
        message: `Aucune donnée comparable pour ${source} vs era5 sur ${variable} à ${targetTimestamp}`,
        hint:
          'ERA5 a une latence de ~5 jours. Choisissez une date plus ancienne ' +
          'ou vérifiez les dates disponibles via GET /api/forecast/available-times?source=era5',
      });
    }

    // 📊 Calcul des stats agrégées (utiles pour la légende de la heatmap)
    let min = Infinity;
    let max = -Infinity;
    let sum = 0;
    let absSum = 0;
    for (const row of result.rows) {
      if (row.error < min) min = row.error;
      if (row.error > max) max = row.error;
      sum += row.error;
      absSum += Math.abs(row.error);
    }
    const n = result.rows.length;

    res.json({
      source,
      comparison: `${source} - era5`,
      variable,
      timestamp: `${date}T${hour}:00:00Z`,
      count: n,
      stats: {
        min: Number(min.toFixed(4)),
        max: Number(max.toFixed(4)),
        mean: Number((sum / n).toFixed(4)),
        abs_mean: Number((absSum / n).toFixed(4)),
      },
      grid: result.rows,
    });
  } catch (err) {
    next(err);
  }
};
