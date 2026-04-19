# Multi-stage build for A2A Registry frontend

# Stage 1: Build the application
FROM node:20-alpine AS builder

WORKDIR /app

# Copy package.json only. Regrettably the host-generated package-lock.json
# omits rollup's platform-specific optional deps for the build image (e.g.
# @rollup/rollup-linux-arm64-musl when developed on darwin-arm64 / linux-gnu)
# and `npm install` in the container refuses to fetch them even with the
# lockfile present — see npm/cli#4828. Until we regenerate the lockfile on a
# matching platform (or enumerate all needed natives under optionalDependencies),
# omitting the lockfile in the builder is the only reliable workaround.
COPY package.json ./

RUN --mount=type=cache,target=/root/.npm \
    npm install --no-audit --no-fund

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
    ASTRO_OUT_DIR=dist

# Build the Astro site; outputs to ./dist inside the image
RUN npm run build

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
