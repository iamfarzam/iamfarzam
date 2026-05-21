# syntax=docker/dockerfile:1.7

# --- Dependencies ---
FROM node:20-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json* ./
RUN --mount=type=cache,target=/root/.npm npm ci --prefer-offline --no-audit --no-fund

# --- Development ---
FROM node:20-alpine AS dev
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
EXPOSE 3000
CMD ["npm", "run", "dev"]

# --- Build ---
FROM node:20-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
ENV NEXT_TELEMETRY_DISABLED=1
ARG NEXT_PUBLIC_API_URL
ARG NEXT_PUBLIC_SITE_URL
ARG NEXT_PUBLIC_SITE_TITLE
ARG NEXT_PUBLIC_REVALIDATE
RUN --mount=type=cache,target=/app/.next/cache npm run build

# --- Production ---
FROM node:20-alpine AS prod
WORKDIR /app
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 nextjs

COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

# next/image optimization requires sharp at runtime in standalone mode;
# otherwise every optimized image request 500s with "sharp is required".
# Install into the standalone bundle's node_modules so server.js resolves it.
RUN npm install --prefix /app sharp && \
    chown -R nextjs:nodejs /app/node_modules /app/package.json /app/package-lock.json 2>/dev/null || true

USER nextjs
EXPOSE 3000
ENV PORT=3000
CMD ["node", "server.js"]
