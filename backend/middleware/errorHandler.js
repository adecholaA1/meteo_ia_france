// ═══════════════════════════════════════════════════════════════════════════
// Météo IA France — Backend
// middleware/errorHandler.js — Gestion centralisée des erreurs
// ─────────────────────────────────────────────────────────────────────────────
// Capture toutes les erreurs des routes/contrôleurs et renvoie un JSON propre.
// Doit être enregistré EN DERNIER dans server.js (après toutes les routes).
//
// Usage dans un contrôleur :
//   try {
//     ...
//   } catch (err) {
//     next(err); // ← passe l'erreur à ce middleware
//   }
//
// Pour créer une erreur custom avec un code HTTP :
//   const err = new Error('Aucune donnée pour cette date');
//   err.statusCode = 404;
//   throw err;
// ═══════════════════════════════════════════════════════════════════════════


function errorHandler(err, req, res, next) {
  // ─── 1. Détermination du code HTTP ─────────────────────────────────────────
  // Si l'erreur a un statusCode défini, on l'utilise
  // Sinon, par défaut 500 (Internal Server Error)
  const statusCode = err.statusCode || err.status || 500;


  // ─── 2. Détection du type d'erreur ─────────────────────────────────────────
  let errorType = 'Internal Server Error';
  let userMessage = 'Une erreur inattendue est survenue.';

  // Erreur PostgreSQL (driver pg)
  // Les codes commencent par des lettres (ex: '42P01' = table inexistante)
  if (err.code && typeof err.code === 'string' && err.code.length === 5) {
    errorType = 'Database Error';
    userMessage = 'Erreur de base de données. Réessaie dans quelques instants.';
    // Ne JAMAIS exposer les détails SQL au frontend (sécurité)
  }
  // Erreur de connexion DB (host injoignable, etc.)
  else if (err.code === 'ECONNREFUSED' || err.code === 'ETIMEDOUT') {
    errorType = 'Database Unavailable';
    userMessage = 'La base de données est temporairement injoignable.';
  }
  // Erreur de validation (créée explicitement par les contrôleurs)
  else if (statusCode === 400) {
    errorType = 'Bad Request';
    userMessage = err.message || 'Requête invalide.';
  }
  // Erreur 404 (créée explicitement par les contrôleurs)
  else if (statusCode === 404) {
    errorType = 'Not Found';
    userMessage = err.message || 'Ressource introuvable.';
  }
  // Toutes les autres erreurs avec un message custom
  else if (err.message && statusCode < 500) {
    errorType = err.name || 'Error';
    userMessage = err.message;
  }


  // ─── 3. Logs côté serveur (toujours détaillés, peu importe l'env) ──────────
  const emoji = statusCode >= 500 ? '🔥' : '⚠️';
  console.error(
    `${emoji} [ErrorHandler] ${req.method} ${req.originalUrl} → ${statusCode}`
  );
  console.error(`   Type    : ${errorType}`);
  console.error(`   Message : ${err.message || '(aucun message)'}`);
  if (err.code) {
    console.error(`   Code    : ${err.code}`);
  }
  // En dev uniquement, on log la stack trace complète
  if (process.env.NODE_ENV === 'development' && err.stack) {
    console.error(`   Stack   :\n${err.stack}`);
  }


  // ─── 4. Réponse JSON au frontend ───────────────────────────────────────────
  const response = {
    error: errorType,
    message: userMessage,
    statusCode,
    timestamp: new Date().toISOString(),
  };

  // En mode développement uniquement, on inclut la stack trace
  // (utile pour debug local, JAMAIS en prod pour ne pas leaker d'infos)
  if (process.env.NODE_ENV === 'development') {
    response.stack = err.stack;
    if (err.code) {
      response.dbCode = err.code;
    }
  }

  res.status(statusCode).json(response);
}


module.exports = errorHandler;
