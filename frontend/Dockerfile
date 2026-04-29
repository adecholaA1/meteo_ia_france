# ============================================================================
# Dockerfile — frontend Vite/React Météo IA France
# ============================================================================
# Stratégie : multi-stage (build avec Node, serve avec Nginx)
# Image finale attendue : ~30 Mo (Nginx alpine + assets bundlés)
#
# Build args (passés via docker-compose ou docker build --build-arg) :
#   VITE_USE_API   : "true" en prod (mode API réelle), "false" pour mock
#   VITE_API_URL   : "/api" en prod (relatif, routé par Nginx host)
# ============================================================================

# ════════════════════════════════════════════════════════════════════════════
# STAGE 1 — "builder" : compile la SPA React/TypeScript avec Vite
# ════════════════════════════════════════════════════════════════════════════
FROM node:22-alpine AS builder

LABEL stage="builder"

WORKDIR /app

# --- Build args reçus depuis docker-compose ou docker build --build-arg ---
# Valeurs par défaut = config production (mode API réelle + URL relative)
ARG VITE_USE_API=true
ARG VITE_API_URL=/api

# --- Exposer les ARG comme variables d'environnement pour Vite ---
# Vite lit process.env.VITE_* et les inline dans le bundle au build
ENV VITE_USE_API=${VITE_USE_API}
ENV VITE_API_URL=${VITE_API_URL}

# --- Installation des dépendances (cache layer) ---
COPY package.json package-lock.json ./

# npm ci = déterministe (utilise package-lock.json à la lettre)
# On garde toutes les deps (devDeps incluses) car Vite et TypeScript
# sont en devDependencies et SONT nécessaires pour le build
RUN npm ci --no-audit --no-fund

# --- Copie du code source ---
# Le .dockerignore exclut .env, node_modules, dist, scripts/, etc.
COPY . .

# --- Build de production ---
# "npm run build" exécute "tsc -b && vite build" (cf. package.json)
# Génère le dossier /app/dist contenant index.html + assets hashés
RUN npm run build

# --- Vérification post-build ---
# Si dist/ est vide ou manque index.html, on échoue le build proprement
RUN test -f /app/dist/index.html || (echo "❌ Build failed: dist/index.html introuvable" && exit 1)


# ════════════════════════════════════════════════════════════════════════════
# STAGE 2 — "production" : sert les fichiers statiques avec Nginx
# ════════════════════════════════════════════════════════════════════════════
FROM nginx:1.27-alpine AS production

LABEL maintainer="Adechola Emile Kouande <kadechola@gmail.com>"
LABEL project="Meteo IA France"
LABEL component="frontend"
LABEL version="1.0.0"

# --- Suppression de la config par défaut de Nginx ---
RUN rm -f /etc/nginx/conf.d/default.conf

# --- Copie de notre config Nginx custom (gzip + cache + SPA fallback) ---
COPY nginx.conf /etc/nginx/conf.d/default.conf

# --- Copie des fichiers buildés depuis le stage "builder" ---
# C'est la magie du multi-stage : on copie SEULEMENT dist/ depuis builder,
# pas Node, pas npm, pas le code source TypeScript. Image finale ultra-light.
COPY --from=builder /app/dist /usr/share/nginx/html

# --- Sécurité : faire tourner Nginx en non-root ---
# L'image nginx:alpine inclut déjà un user "nginx" mais le master Nginx
# tourne en root par défaut (pour pouvoir ouvrir le port 80 réservé < 1024).
# Pour vraiment passer en non-root, il faudrait reconfigurer Nginx pour
# utiliser un port > 1024 (ex: 8080) — on garde la config standard pour V1.0
# car le container est de toute façon isolé.

# --- Port exposé ---
EXPOSE 80

# --- Healthcheck : vérifier que Nginx répond sur /nginx-health ---
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://localhost/nginx-health || exit 1

# --- Démarrage de Nginx en mode foreground (obligatoire pour Docker) ---
# "daemon off" empêche Nginx de se daemoniser, sinon le container exit immédiatement
CMD ["nginx", "-g", "daemon off;"]