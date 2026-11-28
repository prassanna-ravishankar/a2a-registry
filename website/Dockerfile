# Multi-stage build for A2A Registry frontend

# Stage 1: Build the application
FROM node:22-alpine AS builder

WORKDIR /app

COPY package*.json ./

RUN --mount=type=cache,target=/root/.npm \
    npm ci --no-audit --no-fund

# Copy source code
COPY . .

# Build arguments for environment variables
# PUBLIC_POSTHOG_KEY is a public client-side analytics key (not a secret)
# hadolint ignore=DL3044
ARG PUBLIC_API_URL
ARG PUBLIC_POSTHOG_KEY
ARG PUBLIC_POSTHOG_HOST
ENV PUBLIC_API_URL=${PUBLIC_API_URL} \
    PUBLIC_POSTHOG_KEY=${PUBLIC_POSTHOG_KEY} \
    PUBLIC_POSTHOG_HOST=${PUBLIC_POSTHOG_HOST} \
    ASTRO_TELEMETRY_DISABLED=1 \
    ASTRO_OUT_DIR=dist

# The build prerenders agent pages from the live API. A changing value here
# forces a fresh build (and fresh agent data) on scheduled refreshes instead of
# a cached layer.
ARG REGISTRY_REFRESH=""

# Build the Astro site; outputs to ./dist inside the image. The admin key for
# GET /admin/snapshot is a BuildKit secret mounted for this step only, so it is
# never in a layer, the image history or an ENV; postbuild fails the build if it
# shows up in the output. Without the secret the build uses the paced public API.
RUN --mount=type=secret,id=registry_admin_key npm run build

# Stage 2: Serve with nginx
FROM nginx:alpine

# Copy built assets from builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose port 80
EXPOSE 80

# Start nginx
CMD ["nginx", "-g", "daemon off;"]
