// ═══════════════════════════════════════════════════════════════════════════
// Météo IA France — Backend
// routes/healthRoutes.js — Routes de monitoring (santé + état système)
// ─────────────────────────────────────────────────────────────────────────────
// Ces routes ne sont PAS cachées (on veut toujours l'état temps réel).
//
// Endpoints exposés :
//   GET /api/health  → ping rapide (la DB répond ?)
//   GET /api/status  → métriques détaillées (counts par table + cache stats)
// ═══════════════════════════════════════════════════════════════════════════

const express = require('express');
const router = express.Router();
const healthController = require('../controllers/healthController');


// ─── GET /api/health ─────────────────────────────────────────────────────────
// Healthcheck rapide pour Nginx, PM2, UptimeRobot, etc.
// Retourne 200 OK si tout va bien, 503 sinon.
router.get('/health', healthController.getHealth);


// ─── GET /api/status ─────────────────────────────────────────────────────────
// État détaillé du système : taille des tables, dernières dates, stats cache.
// Utile pour debug et pour le frontend (afficher "DB à jour au 24/04/2026").
router.get('/status', healthController.getStatus);


module.exports = router;
