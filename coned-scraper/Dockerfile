ARG BUILD_FROM
FROM $BUILD_FROM

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    gnupg \
    ca-certificates \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libatspi2.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libwayland-client0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxkbcommon0 \
    libxrandr2 \
    xdg-utils \
    libu2f-udev \
    libvulkan1 \
    jq \
    bash \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
WORKDIR /app
COPY python-service/requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Install Playwright browsers
RUN playwright install chromium || true
RUN playwright install-deps chromium || true

# Copy application code
COPY python-service/ ./python-service/

# Create data directory
RUN mkdir -p /data/python-service/data && \
    chmod -R 755 /data

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PLAYWRIGHT_HEADLESS=true

# Copy run script
COPY run.sh /run.sh
RUN chmod a+x /run.sh

CMD [ "/run.sh" ]

LABEL \
  io.hass.version="1.0.0" \
  io.hass.type="addon" \
  io.hass.arch="armhf|aarch64|i386|amd64|armv7"
