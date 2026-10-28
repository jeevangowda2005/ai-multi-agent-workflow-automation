# ── Frontend Dockerfile ───────────────────────────────────────────────────────
# Stage 1: Build the Vite/React app
# Stage 2: Serve the static bundle with nginx
# ─────────────────────────────────────────────────────────────────────────────

# ── Build stage ───────────────────────────────────────────────────────────────
FROM node:20-alpine AS builder

WORKDIR /app

# Install dependencies (leverage layer cache)
COPY package.json package-lock.json ./
RUN npm ci --prefer-offline

# Copy source and build
COPY . .

# VITE_API_BASE_URL can be overridden at build time:
#   docker build --build-arg VITE_API_BASE_URL=http://api.example.com -t frontend .
ARG VITE_API_BASE_URL=http://localhost:8000
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

RUN npm run build

# ── Production stage ──────────────────────────────────────────────────────────
FROM nginx:1.25-alpine

# Remove default nginx static content
RUN rm -rf /usr/share/nginx/html/*

# Copy built assets from builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

# nginx config: serve SPA with fallback to index.html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD wget -qO- http://localhost/index.html || exit 1

CMD ["nginx", "-g", "daemon off;"]
