/**
 * ============================================================================
 *  📁 controllers/forecastController.js
 * ----------------------------------------------------------------------------
 *  Logique métier pour les routes /api/forecast/*
 *
 *  Toutes les fonctions :
 *    - sont async (req, res, next)
 *    - utilisent pool.query() de config/db.js
 *    - en cas d'erreur, appellent next(err) → errorHandler centralisé
 *    - utilisent les VUES *_fresh quand pertinent (pas les tables brutes)
 *
 *  📚 Rappel des tables / vues utilisées :
 *    - graphcast_predictions_fresh  (vue : 1 ligne par tuple, run le + récent)
 *    - arome_forecasts_fresh        (vue : idem)
 *    - era5_truth                   (table directe, pas de notion de "run")
 * ============================================================================
 */

const { pool } = require('../config/db');

// ----------------------------------------------------------------------------
// 🔧 CONSTANTES
// ----------------------------------------------------------------------------

// Mapping source → table/vue à interroger
const SOURCE_TO_TABLE = {
  graphcast: 'graphcast_predictions_fresh',
  arome: 'arome_forecasts_fresh',
  era5: 'era5_truth',
};

// Variables exposées au frontend (alignées avec le projet)
const ALLOWED_VARIABLES = [
  't2m_celsius',
  'wind_speed_10m_ms',
  'wind_direction_10m_deg',
  'msl_hpa',
  'tp_6h_mm',
  'toa_wm2',
];

// Point GPS par défaut = Paris (cohérent avec ai-elec-conso)
const DEFAULT_LAT = 48.75;
const DEFAULT_LON = 2.5;

// ----------------------------------------------------------------------------
// 🛠️ HELPERS
// ----------------------------------------------------------------------------

/**
 * Valide et normalise le paramètre `source`.
 * @returns {string} nom de table/vue à utiliser
 * @throws {Error} si la source est invalide (status 400)
 */
function resolveSource(sourceParam) {
  const source = (sourceParam || 'graphcast').toLowerCase();
  const table = SOURCE_TO_TABLE[source];
  if (!table) {
    const err = new Error(
      `Source invalide : "${source}". Valeurs autorisées : ${Object.keys(
        SOURCE_TO_TABLE
      ).join(', ')}`
    );
    err.status = 400;
    throw err;
  }
  return { source, table };
}

/**
 * Valide une variable météo.
 */
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
//  1️⃣  GET /api/forecast/available-times
// ============================================================================

/**
 * Retourne la liste des couples (date, heure) disponibles pour une source.
 *
 * Exemple de réponse :
 * {
 *   "source": "graphcast",
 *   "count": 32,
 *   "times": [
 *     { "date": "2026-04-18", "hour": "00", "horizons": [6,12,18,24] },
 *     { "date": "2026-04-18", "hour": "06", "horizons": [6,12,18,24] },
 *     ...
 *   ]
 * }
 */
exports.getAvailableTimes = async (req, res, next) => {
  try {
    const { source, table } = resolveSource(req.query.source);

    let sql;
    if (source === 'era5') {
      // ERA5 : pas de notion de horizon, juste les timestamps disponibles
      sql = `
        SELECT
          TO_CHAR(timestamp AT TIME ZONE 'UTC', 'YYYY-MM-DD') AS date,
          TO_CHAR(timestamp AT TIME ZONE 'UTC', 'HH24')        AS hour
        FROM ${table}
        GROUP BY date, hour
        ORDER BY date DESC, hour DESC
      `;
      const result = await pool.query(sql);
      return res.json({
        source,
        count: result.rows.length,
        times: result.rows.map((r) => ({ ...r, horizons: [0] })),
      });
    }

    // GraphCast / AROME : on agrège par (date, hour) avec liste des horizons
    sql = `
      SELECT
        TO_CHAR(timestamp AT TIME ZONE 'UTC', 'YYYY-MM-DD') AS date,
        TO_CHAR(timestamp AT TIME ZONE 'UTC', 'HH24')        AS hour,
        ARRAY_AGG(DISTINCT forecast_horizon_h ORDER BY forecast_horizon_h) AS horizons
      FROM ${table}
      GROUP BY date, hour
      ORDER BY date DESC, hour DESC
    `;
    const result = await pool.query(sql);
    res.json({
      source,
      count: result.rows.length,
      times: result.rows,
    });
  } catch (err) {
    next(err);
  }
};

// ============================================================================
//  2️⃣  GET /api/forecast/grid-points
// ============================================================================

/**
 * Retourne les 2925 points GPS uniques de la grille.
 *
 * Exemple de réponse :
 * {
 *   "count": 2925,
 *   "points": [
 *     { "lat": 41.0,  "lon": -5.5 },
 *     { "lat": 41.0,  "lon": -5.25 },
 *     ...
 *   ]
 * }
 *
 * Note : on requête era5_truth car c'est la source la plus stable (vérité).
 *        On pourrait aussi faire UNION DISTINCT sur les 3 tables mais c'est
 *        plus lent et inutile (la grille est identique partout).
 */
exports.getGridPoints = async (req, res, next) => {
  try {
    const sql = `
      SELECT DISTINCT
        latitude::float  AS lat,
        longitude::float AS lon
      FROM era5_truth
      ORDER BY lat, lon
    `;
    const result = await pool.query(sql);
    res.json({
      count: result.rows.length,
      points: result.rows,
    });
  } catch (err) {
    next(err);
  }
};

// ============================================================================
//  3️⃣  GET /api/forecast/timeseries
// ============================================================================

/**
 * Retourne 7j de séries temporelles pour 1 point GPS, toutes variables, 3 sources.
 *
 * Format de réponse optimisé pour Recharts :
 * {
 *   "point": { "lat": 48.75, "lon": 2.5 },
 *   "days": 7,
 *   "variables": {
 *     "t2m_celsius": [
 *       { "timestamp": "2026-04-18T00:00:00Z", "graphcast": 8.5, "arome": 8.7, "era5": 8.6 },
 *       { "timestamp": "2026-04-18T06:00:00Z", "graphcast": 6.2, "arome": 6.3, "era5": null },
 *       ...
 *     ],
 *     "wind_speed_10m_ms": [...],
 *     ...
 *   }
 * }
 *
 * Note : era5 peut être null pour les timestamps récents (latence J-5).
 */
exports.getTimeseries = async (req, res, next) => {
  try {
    const lat = parseFloat(req.query.lat) || DEFAULT_LAT;
    const lon = parseFloat(req.query.lon) || DEFAULT_LON;
    const days = Math.min(parseInt(req.query.days, 10) || 7, 30);

    // 🎯 Une seule requête SQL avec FULL OUTER JOIN sur les 3 sources
    // pour assembler les courbes superposées par (timestamp, variable).
    const sql = `
      WITH
      gc AS (
        SELECT timestamp, variable_name, value::float AS value
        FROM graphcast_predictions_fresh
        WHERE latitude = $1 AND longitude = $2
          AND variable_name = ANY($3::text[])
          AND timestamp >= NOW() - ($4 || ' days')::interval
      ),
      ar AS (
        SELECT timestamp, variable_name, value::float AS value
        FROM arome_forecasts_fresh
        WHERE latitude = $1 AND longitude = $2
          AND variable_name = ANY($3::text[])
          AND timestamp >= NOW() - ($4 || ' days')::interval
      ),
      er AS (
        SELECT timestamp, variable_name, value::float AS value
        FROM era5_truth
        WHERE latitude = $1 AND longitude = $2
          AND variable_name = ANY($3::text[])
          AND timestamp >= NOW() - ($4 || ' days')::interval
      ),
      all_keys AS (
        SELECT timestamp, variable_name FROM gc
        UNION
        SELECT timestamp, variable_name FROM ar
        UNION
        SELECT timestamp, variable_name FROM er
      )
      SELECT
        TO_CHAR(k.timestamp AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"') AS timestamp,
        k.variable_name,
        gc.value AS graphcast,
        ar.value AS arome,
        er.value AS era5
      FROM all_keys k
      LEFT JOIN gc ON gc.timestamp = k.timestamp AND gc.variable_name = k.variable_name
      LEFT JOIN ar ON ar.timestamp = k.timestamp AND ar.variable_name = k.variable_name
      LEFT JOIN er ON er.timestamp = k.timestamp AND er.variable_name = k.variable_name
      ORDER BY k.variable_name, k.timestamp
    `;

    const result = await pool.query(sql, [
      lat,
      lon,
      ALLOWED_VARIABLES,
      days,
    ]);

    // 🔄 Pivot : on regroupe les rows par variable_name pour faciliter le frontend
    const variables = {};
    for (const v of ALLOWED_VARIABLES) variables[v] = [];

    for (const row of result.rows) {
      variables[row.variable_name].push({
        timestamp: row.timestamp,
        graphcast: row.graphcast,
        arome: row.arome,
        era5: row.era5,
      });
    }

    res.json({
      point: { lat, lon },
      days,
      variables,
    });
  } catch (err) {
    next(err);
  }
};

// ============================================================================
//  4️⃣  GET /api/forecast/:date/:hour
// ============================================================================

/**
 * Retourne la grille complète (2925 points) à un instant T pour 1 source/variable.
 * Sert principalement à la HEATMAP du frontend.
 *
 * Exemple de réponse :
 * {
 *   "source": "graphcast",
 *   "variable": "t2m_celsius",
 *   "timestamp": "2026-04-25T12:00:00Z",
 *   "count": 2925,
 *   "grid": [
 *     { "lat": 41.0, "lon": -5.5, "value": 14.2 },
 *     ...
 *   ]
 * }
 */
exports.getForecastByDateHour = async (req, res, next) => {
  try {
    const { date, hour } = req.params;
    const { source, table } = resolveSource(req.query.source);
    const variable = req.query.variable || 't2m_celsius';
    validateVariable(variable);

    // Validation simple du format date/hour
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

    const sql = `
      SELECT
        latitude::float  AS lat,
        longitude::float AS lon,
        value::float     AS value
      FROM ${table}
      WHERE timestamp = $1::timestamptz
        AND variable_name = $2
      ORDER BY lat, lon
    `;
    const result = await pool.query(sql, [targetTimestamp, variable]);

    if (result.rows.length === 0) {
      return res.status(404).json({
        status: 'not_found',
        message: `Aucune donnée pour ${source}/${variable} à ${targetTimestamp}`,
        hint: 'Vérifiez les dates disponibles via GET /api/forecast/available-times',
      });
    }

    res.json({
      source,
      variable,
      timestamp: `${date}T${hour}:00:00Z`,
      count: result.rows.length,
      grid: result.rows,
    });
  } catch (err) {
    next(err);
  }
};
