// ═══════════════════════════════════════════════════════════════════════════
// Météo IA France — Backend
// middleware/cache.js — Cache RAM pour les routes lourdes
// ─────────────────────────────────────────────────────────────────────────────
// Évite de hammer la DB à chaque visiteur en mémorisant les réponses
// pendant CACHE_TTL_SECONDS (par défaut 600s = 10 min, conforme HANDOFF).
//
// Usage dans une route :
//   const cache = require('../middleware/cache');
//   router.get('/timeseries', cache(), forecastController.getTimeseries);
//
// Pour bypasser le cache sur une route (ex: /api/health) :
//   ne pas mettre le middleware cache().
//
// Pour vider tout le cache manuellement (ex: après un cron data) :
//   cache.flush();
// ═══════════════════════════════════════════════════════════════════════════

const NodeCache = require('node-cache');


// ─── Instance globale du cache ──────────────────────────────────────────────
// stdTTL : durée de vie par défaut (en secondes)
// checkperiod : fréquence de purge des clés expirées (en secondes)
// useClones : false = on stocke par référence (plus rapide, mais à manier avec soin)
const cacheInstance = new NodeCache({
  stdTTL: parseInt(process.env.CACHE_TTL_SECONDS, 10) || 600,
  checkperiod: 120,
  useClones: false,
});


// ─── Statistiques (utile pour debug) ────────────────────────────────────────
let stats = {
  hits: 0,    // Cache trouvé → DB pas appelée
  misses: 0,  // Cache absent → DB appelée
};


// ─── Middleware factory ──────────────────────────────────────────────────────
// On expose une fonction qui retourne le vrai middleware.
// Permet à l'avenir de personnaliser la durée par route :
//   cache(60)  → cache 60s pour cette route uniquement
function cache(ttlSeconds = null) {
  return (req, res, next) => {
    // ─── 1. Construction de la clé ─────────────────────────────────────────
    // Clé basée sur méthode HTTP + URL complète (avec query params)
    const key = `${req.method}:${req.originalUrl}`;


    // ─── 2. Lookup dans le cache ───────────────────────────────────────────
    const cached = cacheInstance.get(key);
    if (cached !== undefined) {
      stats.hits += 1;
      // En mode dev, on signale que c'est un hit cache
      if (process.env.NODE_ENV === 'development') {
        console.log(`💚 [Cache HIT]  ${key}`);
      }
      // On ajoute un en-tête pour informer le frontend (utile pour debug)
      res.set('X-Cache', 'HIT');
      return res.status(200).json(cached);
    }


    // ─── 3. Cache miss : on intercepte res.json() pour sauvegarder ─────────
    stats.misses += 1;
    if (process.env.NODE_ENV === 'development') {
      console.log(`🔶 [Cache MISS] ${key}`);
    }
    res.set('X-Cache', 'MISS');

    // On garde la fonction originale res.json
    const originalJson = res.json.bind(res);

    // On la remplace par une version qui sauvegarde avant d'envoyer
    res.json = (body) => {
      // On ne cache que les réponses 2xx (succès)
      if (res.statusCode >= 200 && res.statusCode < 300) {
        const ttl = ttlSeconds || cacheInstance.options.stdTTL;
        cacheInstance.set(key, body, ttl);
      }
      return originalJson(body);
    };

    next();
  };
}


// ─── Helpers exportés ────────────────────────────────────────────────────────
// Vider TOUT le cache (utile en debug, ou après un import massif de données)
cache.flush = () => {
  cacheInstance.flushAll();
  stats = { hits: 0, misses: 0 };
  console.log('🗑️  [Cache] Vidé entièrement');
};

// Récupérer les stats (utile pour route /api/status)
cache.getStats = () => {
  const total = stats.hits + stats.misses;
  const hitRate = total > 0 ? ((stats.hits / total) * 100).toFixed(1) : '0.0';
  return {
    keys: cacheInstance.keys().length,
    hits: stats.hits,
    misses: stats.misses,
    hitRate: `${hitRate}%`,
    ttl_seconds: cacheInstance.options.stdTTL,
  };
};

// Invalider une clé spécifique (utile si tu sais qu'une donnée vient de changer)
cache.invalidate = (key) => {
  cacheInstance.del(key);
};


module.exports = cache;
