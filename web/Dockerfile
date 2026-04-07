# ─── RootOps Web — Containerised Next.js ─────────────────────────
# Supply chain isolation: node_modules never touch the host.
# All npm operations run inside this container.
#
# Multi-stage:
#   1. deps   → install dependencies (cached layer)
#   2. dev    → development target (hot-reload via bind mount)
#   3. build  → production build
#   4. prod   → minimal production image

# ── Stage 1: dependency installation ──────────────────────────────
FROM node:22-alpine AS deps

# Security: run npm in a restricted env
RUN apk add --no-cache libc6-compat
WORKDIR /app

# Copy only package manifests — maximise Docker layer cache
COPY package.json package-lock.json* .npmrc ./

# npm ci = lockfile-only install (fails if lockfile is out of sync)
# --ignore-scripts is also in .npmrc but we double-enforce it here
RUN npm ci --ignore-scripts 2>&1

# ── Stage 2: development (used by docker-compose) ────────────────
FROM node:22-alpine AS dev

WORKDIR /app

# Copy installed node_modules from deps stage
COPY --from=deps /app/node_modules ./node_modules

# Source code is bind-mounted at runtime (see docker-compose.yml)
# so we only copy config files needed before the mount is ready
COPY package.json .npmrc next.config.ts tsconfig.json postcss.config.mjs ./

# Non-root user
RUN addgroup -g 1001 -S rootops && \
    adduser -S rootops -u 1001 -G rootops && \
    chown -R rootops:rootops /app
USER rootops

EXPOSE 3000

ENV PORT=3000
ENV HOSTNAME="0.0.0.0"
ENV NODE_ENV=development
# Disable Next.js telemetry
ENV NEXT_TELEMETRY_DISABLED=1

CMD ["npm", "run", "dev"]

# ── Stage 3: production build ────────────────────────────────────
FROM node:22-alpine AS build

WORKDIR /app

COPY --from=deps /app/node_modules ./node_modules
COPY . .

ENV NEXT_TELEMETRY_DISABLED=1

RUN npm run build

# ── Stage 4: production runtime ──────────────────────────────────
FROM node:22-alpine AS prod

WORKDIR /app

RUN addgroup -g 1001 -S rootops && \
    adduser -S rootops -u 1001 -G rootops

# Copy only what's needed to run
COPY --from=build /app/public ./public
COPY --from=build --chown=rootops:rootops /app/.next/standalone ./
COPY --from=build --chown=rootops:rootops /app/.next/static ./.next/static

USER rootops

EXPOSE 3000

ENV PORT=3000
ENV HOSTNAME="0.0.0.0"
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:3000/ || exit 1

CMD ["node", "server.js"]
