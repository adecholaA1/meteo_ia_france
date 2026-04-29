# ============================================================================
# Dockerfile — backend Express Météo IA France
# ============================================================================
# Stratégie : single-stage Node 22 alpine + utilisateur non-root
# Image finale attendue : ~150 Mo
# ============================================================================

# ---- Étape unique : build + run ----
# node:22-alpine = Node.js 22 LTS sur Alpine Linux (~50 Mo de base)
# alpine = distribution Linux ultra-légère, parfaite pour Docker
FROM node:22-alpine

# --- Métadonnées de l'image (utile pour debug et registries) ---
LABEL maintainer="Adechola Emile Kouande <kadechola@gmail.com>"
LABEL project="Meteo IA France"
LABEL component="backend"
LABEL version="1.0.0"

# --- Définir le dossier de travail dans le container ---
# Tout ce qui suit (COPY, RUN, CMD) se passe dans /app
WORKDIR /app

# --- Installer les dépendances système nécessaires ---
# Aucune ! Express + pg + node-cache n'ont pas besoin de libs natives.
# Si plus tard on ajoute bcrypt ou sharp, il faudra ajouter :
# RUN apk add --no-cache python3 make g++

# --- Copier UNIQUEMENT les fichiers de dépendances d'abord ---
# Astuce de cache Docker : si package.json ne change pas, on saute le npm ci
# et on réutilise la couche cachée → builds beaucoup plus rapides
COPY package.json package-lock.json ./

# --- Installer les dépendances de PRODUCTION uniquement ---
# npm ci = installation déterministe basée sur package-lock.json
# --omit=dev = exclut les devDependencies (nodemon n'est pas embarqué)
# --no-audit --no-fund = silencieux et plus rapide
RUN npm ci --omit=dev --no-audit --no-fund && \
    npm cache clean --force

# --- Copier le reste du code ---
# Le .dockerignore exclut .env, node_modules, .git, logs, etc.
COPY . .

# --- Sécurité : créer/utiliser un utilisateur non-root ---
# L'image node:alpine inclut déjà un user "node" (UID 1000)
# On change le propriétaire de /app pour cet utilisateur
RUN chown -R node:node /app

# Bascule sur l'utilisateur non-root pour tout ce qui suit
USER node

# --- Documenter le port exposé ---
# EXPOSE est purement informatif (n'ouvre pas réellement le port —
# c'est docker-compose ou docker run -p qui s'en occupe)
EXPOSE 3001

# --- Healthcheck : Docker vérifie que le backend répond ---
# Toutes les 30s, fait un appel à /api/health (à condition que
# cet endpoint existe dans ton server.js — sinon adapter)
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD node -e "require('http').get('http://localhost:3001/api/health', (r) => process.exit(r.statusCode === 200 ? 0 : 1)).on('error', () => process.exit(1))"

# --- Commande de démarrage ---
# Pas npm start (overhead inutile + npm intercepte les signaux SIGTERM)
# Lancer node directement = meilleur pour la prod
CMD ["node", "server.js"]
