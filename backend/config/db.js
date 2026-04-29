// ═══════════════════════════════════════════════════════════════════════════
// Météo IA France — Backend
// config/db.js — Pool de connexions PostgreSQL
// ─────────────────────────────────────────────────────────────────────────────
// Centralise la connexion à la DB pour tous les contrôleurs.
// Utilise un Pool (10 connexions par défaut) pour des performances optimales.
// ═══════════════════════════════════════════════════════════════════════════

const { Pool } = require('pg');

// ─── Configuration du Pool ───────────────────────────────────────────────────
// Les credentials sont lus depuis .env (chargés par dotenv dans server.js)
const pool = new Pool({
  host: process.env.DB_HOST,
  port: parseInt(process.env.DB_PORT, 10),
  database: process.env.DB_NAME,
  user: process.env.DB_USER,
  password: process.env.DB_PASSWORD,

  // ─── Tuning du pool ───────────────────────────────────────────────────────
  max: 10,                       // Max 10 connexions simultanées (largement suffisant pour MVP)
  idleTimeoutMillis: 30_000,     // Ferme une connexion inactive après 30s
  connectionTimeoutMillis: 5_000, // Échoue si pas connecté après 5s
});

// ─── Gestion d'erreur globale du pool ────────────────────────────────────────
// Capture les erreurs d'une connexion idle qui meurt côté PostgreSQL
pool.on('error', (err) => {
  console.error('❌ [DB] Erreur inattendue sur une connexion idle:', err.message);
  // On ne crash pas le process — le pool va recréer une connexion automatiquement
});


// ─── Helper query() ──────────────────────────────────────────────────────────
// Wrapper autour de pool.query() avec logs en mode dev.
// Usage : const { rows } = await query('SELECT * FROM era5_truth WHERE ...', [params]);
async function query(text, params = []) {
  const start = Date.now();
  try {
    const result = await pool.query(text, params);
    const duration = Date.now() - start;

    // En mode développement, on log les requêtes lentes (>100ms)
    if (process.env.NODE_ENV === 'development' && duration > 100) {
      console.log(`🐢 [DB] Requête lente (${duration}ms): ${text.substring(0, 80)}...`);
    }

    return result;
  } catch (err) {
    console.error(`❌ [DB] Erreur SQL:`, err.message);
    console.error(`   Query: ${text.substring(0, 200)}`);
    if (params.length > 0) {
      console.error(`   Params:`, params);
    }
    throw err; // On re-throw pour que le contrôleur gère via errorHandler
  }
}


// ─── Healthcheck au démarrage ────────────────────────────────────────────────
// Vérifie que la DB répond avant de lancer le serveur.
// Si la DB n'est pas accessible, on affiche un message clair.
async function checkConnection() {
  try {
    const result = await pool.query('SELECT NOW() AS current_time, version() AS pg_version');
    const { current_time, pg_version } = result.rows[0];

    console.log('✅ [DB] Connexion PostgreSQL OK');
    console.log(`   ├─ Hôte     : ${process.env.DB_HOST}:${process.env.DB_PORT}`);
    console.log(`   ├─ Base     : ${process.env.DB_NAME}`);
    console.log(`   ├─ Heure DB : ${current_time.toISOString()}`);
    console.log(`   └─ Version  : ${pg_version.split(' ').slice(0, 2).join(' ')}`);

    return true;
  } catch (err) {
    console.error('❌ [DB] Impossible de se connecter à PostgreSQL:');
    console.error(`   Erreur : ${err.message}`);
    console.error(`   Vérifie : `);
    console.error(`   1. Le container Docker meteo_ia_pg_db est-il démarré ?`);
    console.error(`      → docker ps | grep meteo_ia_pg_db`);
    console.error(`   2. Les credentials du .env sont-ils corrects ?`);
    console.error(`      → cat backend/.env`);
    console.error(`   3. Le port ${process.env.DB_PORT} est-il bien le bon ?`);
    return false;
  }
}


// ─── Graceful shutdown ───────────────────────────────────────────────────────
// Quand le serveur s'arrête (Ctrl+C, SIGTERM), ferme proprement le pool
async function closePool() {
  try {
    await pool.end();
    console.log('✅ [DB] Pool de connexions fermé proprement');
  } catch (err) {
    console.error('❌ [DB] Erreur lors de la fermeture du pool:', err.message);
  }
}


// ─── Exports ─────────────────────────────────────────────────────────────────
module.exports = {
  pool,            // Le pool brut (au cas où on en a besoin pour des transactions)
  query,           // Helper standard à utiliser partout
  checkConnection, // Pour le startup
  closePool,       // Pour le shutdown
};
