// ═══════════════════════════════════════════════════════════════════════════
// Météo IA France — Backend
// server.js — Point d'entrée Express
// ─────────────────────────────────────────────────────────────────────────────
// Démarre le serveur HTTP, configure les middlewares (CORS, rate-limit, etc.)
// et branche toutes les routes API.
//
// Lancement :
//   npm start       (production)
//   npm run dev     (avec auto-reload via nodemon)
// ═══════════════════════════════════════════════════════════════════════════


// ─── 1. Chargement des variables d'environnement ─────────────────────────────
// DOIT être la TOUTE PREMIÈRE chose : sinon db.js essaiera de lire .env vide
require('dotenv').config();


// ─── 2. Imports ──────────────────────────────────────────────────────────────
const express = require('express');
const cors = require('cors');
const rateLimit = require('express-rate-limit');

const { checkConnection, closePool } = require('./config/db');

// Routes (on les créera juste après — pour l'instant, fichiers vides OK)
const healthRoutes = require('./routes/healthRoutes');
const forecastRoutes = require('./routes/forecastRoutes');
const maeRoutes = require('./routes/maeRoutes');
const heatmapRoutes = require('./routes/heatmapRoutes');

// Middleware d'erreur centralisé
const errorHandler = require('./middleware/errorHandler');


// ─── 3. Initialisation Express ───────────────────────────────────────────────
const app = express();
const PORT = parseInt(process.env.PORT, 10) || 3001;
const NODE_ENV = process.env.NODE_ENV || 'development';


// ─── 4. Middlewares globaux ──────────────────────────────────────────────────

// 4.1 — CORS : autorise le frontend (autre origine) à appeler cette API
const corsOrigins = (process.env.CORS_ORIGINS || 'http://localhost:5173')
  .split(',')
  .map((o) => o.trim());

app.use(
  cors({
    origin: corsOrigins,
    methods: ['GET', 'POST'], // 🆕 PHASE B.6 : POST ajouté pour /cache/clear
    credentials: false, // Pas de cookies/auth pour le MVP
  })
);

// 4.2 — JSON parser : pour parser les body JSON (utile en v2.0 si POST)
app.use(express.json());

// 4.3 — Logger HTTP simple (en mode dev uniquement)
if (NODE_ENV === 'development') {
  app.use((req, res, next) => {
    const start = Date.now();
    res.on('finish', () => {
      const duration = Date.now() - start;
      const emoji = res.statusCode < 400 ? '✅' : '❌';
      console.log(
        `${emoji} ${req.method} ${req.originalUrl} → ${res.statusCode} (${duration}ms)`
      );
    });
    next();
  });
}

// 4.4 — Rate limiting : 100 req/h/IP (HANDOFF)
const limiter = rateLimit({
  windowMs: parseInt(process.env.RATE_LIMIT_WINDOW_MIN, 10) * 60 * 1000,
  max: parseInt(process.env.RATE_LIMIT_MAX, 10),
  standardHeaders: true,  // Retourne les en-têtes RateLimit-* dans la réponse
  legacyHeaders: false,
  message: {
    error: 'Too many requests',
    message: 'Tu as dépassé la limite de requêtes par heure. Réessaie plus tard.',
  },
});
app.use('/api/', limiter); // S'applique uniquement aux routes /api/*


// ─── 5. Routes API ───────────────────────────────────────────────────────────
app.use('/api', healthRoutes);     // /api/health, /api/status
app.use('/api/forecast', forecastRoutes); // /api/forecast/*
app.use('/api/mae', maeRoutes);    // /api/mae/*
app.use('/api/heatmap', heatmapRoutes); // /api/heatmap/*

// Route racine pour confirmer que le serveur tourne
app.get('/', (req, res) => {
  res.json({
    name: 'Météo IA France API',
    version: '1.0.0',
    status: 'running',
    docs: '/api/health',
    endpoints: [
      'GET /api/health',
      'GET /api/status',
      'GET /api/forecast/available-times',
      'GET /api/forecast/:date/:hour',
      'GET /api/forecast/timeseries',
      'GET /api/forecast/grid-points',
      'POST /api/forecast/cache/clear',
      'GET /api/mae/comparison',
      'GET /api/heatmap/error',
    ],
  });
});


// ─── 6. Gestion des routes inexistantes (404) ────────────────────────────────
app.use((req, res) => {
  res.status(404).json({
    error: 'Not Found',
    message: `La route ${req.method} ${req.originalUrl} n'existe pas`,
    hint: 'Consulte GET / pour voir la liste des endpoints disponibles',
  });
});


// ─── 7. Middleware d'erreur centralisé (catch all) ───────────────────────────
// DOIT être en DERNIER (après toutes les routes)
app.use(errorHandler);


// ═════════════════════════════════════════════════════════════════════════════
// 🆕 PHASE B.6 — Pre-warming du cache au démarrage
// ─────────────────────────────────────────────────────────────────────────────
// Au démarrage du backend, on pré-remplit le cache des 3 sources pour que
// le 1er utilisateur n'ait pas à attendre 6-9s. Le pré-remplissage est
// asynchrone (non-bloquant) : Express commence à écouter immédiatement,
// et le cache se rempli en arrière-plan dans les ~10-30 secondes qui suivent.
//
// Tolérant aux pannes : si la DB n'est pas dispo ou si le pre-warming échoue,
// on log un warning mais on ne bloque PAS le démarrage.
// ═════════════════════════════════════════════════════════════════════════════

async function preWarmCache() {
  const sources = ['arome', 'graphcast', 'era5'];
  console.log('🔥 [Pre-warming] Démarrage en arrière-plan...');

  for (const source of sources) {
    try {
      const url = `http://localhost:${PORT}/api/forecast/available-times?source=${source}`;
      const startTime = Date.now();
      const response = await fetch(url);
      const elapsed = Date.now() - startTime;

      if (response.ok) {
        console.log(
          `🔥 [Pre-warming] ✅ ${source} pré-réchauffé en ${elapsed}ms`
        );
      } else {
        console.warn(
          `🔥 [Pre-warming] ⚠️  ${source} : HTTP ${response.status}`
        );
      }
    } catch (err) {
      console.warn(`🔥 [Pre-warming] ⚠️  ${source} : ${err.message}`);
    }
  }

  console.log('🔥 [Pre-warming] Terminé');
}


// ─── 8. Démarrage du serveur (avec healthcheck DB) ───────────────────────────
async function startServer() {
  console.log('═══════════════════════════════════════════════════════════════');
  console.log('🌦️  Météo IA France — Backend Express');
  console.log(`   Mode    : ${NODE_ENV}`);
  console.log(`   Port    : ${PORT}`);
  console.log(`   CORS    : ${corsOrigins.join(', ')}`);
  console.log('═══════════════════════════════════════════════════════════════');

  // Healthcheck DB AVANT de démarrer Express
  const dbOk = await checkConnection();
  if (!dbOk) {
    console.error('❌ Démarrage annulé : la DB n\'est pas accessible.');
    process.exit(1);
  }

  // Démarrage Express
  const server = app.listen(PORT, () => {
    console.log(`🚀 [Express] Serveur démarré sur http://localhost:${PORT}`);
    console.log(`   Test rapide : curl http://localhost:${PORT}/api/health`);
    console.log('═══════════════════════════════════════════════════════════════\n');

    // 🆕 PHASE B.6 — Lance le pre-warming en arrière-plan (non bloquant)
    // On attend 1s pour que le serveur soit complètement prêt à recevoir
    // les requêtes HTTP locales du pre-warming.
    setTimeout(() => {
      preWarmCache().catch((err) => {
        console.warn(`🔥 [Pre-warming] ⚠️  Erreur globale : ${err.message}`);
      });
    }, 1000);
  });

  // ─── Graceful shutdown ─────────────────────────────────────────────────────
  // Quand on fait Ctrl+C ou kill, on ferme proprement
  const shutdown = async (signal) => {
    console.log(`\n⚠️  Signal reçu : ${signal}. Arrêt en cours...`);
    server.close(async () => {
      console.log('✅ [Express] Serveur HTTP fermé');
      await closePool();
      console.log('👋 Au revoir !');
      process.exit(0);
    });

    // Si dans 10s on n'a pas réussi à fermer, on force
    setTimeout(() => {
      console.error('❌ Arrêt forcé après timeout');
      process.exit(1);
    }, 10_000);
  };

  process.on('SIGINT', () => shutdown('SIGINT'));   // Ctrl+C
  process.on('SIGTERM', () => shutdown('SIGTERM')); // kill / Docker stop
}


// ─── Lancement ───────────────────────────────────────────────────────────────
startServer().catch((err) => {
  console.error('❌ Erreur fatale au démarrage:', err);
  process.exit(1);
});
