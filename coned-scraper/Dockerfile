# Stage 1: Build Next.js with addon API URL (same-container backend)
FROM node:20-bookworm-slim AS nextjs-builder
WORKDIR /app

COPY app/package*.json ./
RUN npm ci

COPY app/ ./
RUN chmod -R +x node_modules/.bin 2>/dev/null || true

ENV DOCKER_BUILD=true
ENV API_BASE_URL=http://127.0.0.1:8000
RUN npm run build

# Stage 2: Addon image with Node + Python + both apps
ARG BUILD_FROM=ghcr.io/hassio-addons/base:20.0.1
FROM ${BUILD_FROM}

RUN apk add --no-cache \
    nodejs \
    npm \
    python3 \
    py3-pip \
    && rm -rf /var/cache/apk/*

WORKDIR /app

# Copy Python service and install dependencies
COPY python-service/requirements.txt /app/python-service/
RUN pip3 install --no-cache-dir -r /app/python-service/requirements.txt

# Install Playwright Chromium and system dependencies
RUN python3 -m playwright install chromium && python3 -m playwright install-deps chromium

# Copy full Python service
COPY python-service/ /app/python-service/

# Copy Next.js standalone output
COPY --from=nextjs-builder /app/.next/standalone ./web/
COPY --from=nextjs-builder /app/.next/static ./web/.next/static
COPY --from=nextjs-builder /app/public ./web/public

# Copy root filesystem (S6 overlay)
COPY rootfs /
RUN chmod +x /etc/s6-overlay/s6-rc.d/init-coned/run \
    /etc/s6-overlay/s6-rc.d/api/run /etc/s6-overlay/s6-rc.d/api/finish \
    /etc/s6-overlay/s6-rc.d/web/run /etc/s6-overlay/s6-rc.d/web/finish

# Build arguments
ARG BUILD_ARCH
ARG BUILD_DATE
ARG BUILD_DESCRIPTION
ARG BUILD_NAME
ARG BUILD_REF
ARG BUILD_REPOSITORY
ARG BUILD_VERSION

# Labels
LABEL \
    io.hass.name="${BUILD_NAME}" \
    io.hass.description="${BUILD_DESCRIPTION}" \
    io.hass.arch="${BUILD_ARCH}" \
    io.hass.type="addon" \
    io.hass.version=${BUILD_VERSION} \
    maintainer="ConEd Scraper" \
    org.opencontainers.image.title="${BUILD_NAME}" \
    org.opencontainers.image.description="${BUILD_DESCRIPTION}" \
    org.opencontainers.image.vendor="ConEd Scraper" \
    org.opencontainers.image.licenses="MIT" \
    org.opencontainers.image.source="https://github.com/${BUILD_REPOSITORY}" \
    org.opencontainers.image.documentation="https://github.com/${BUILD_REPOSITORY}/blob/main/README.md" \
    org.opencontainers.image.created=${BUILD_DATE} \
    org.opencontainers.image.revision=${BUILD_REF} \
    org.opencontainers.image.version=${BUILD_VERSION}
