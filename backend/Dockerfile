# Scanner Worker (Backend + Scanner)

FROM node:20.19.2-bullseye-slim AS reporting-build

WORKDIR /app/scanner/reporting
COPY scanner/reporting/package*.json ./
RUN if [ -f package-lock.json ]; then npm ci; else npm install; fi
COPY scanner/reporting/ ./
RUN node node_modules/typescript/bin/tsc

FROM python:3.11-slim

# Install docker-compose, gosu, curl, and git for runtime execution
RUN apt-get update && apt-get install -y \
    curl \
    gosu \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install docker CLI (standalone binary - version 26.1.4)
RUN curl -L "https://download.docker.com/linux/static/stable/x86_64/docker-26.1.4.tgz" -o /tmp/docker.tgz \
    && tar -xz -C /tmp -f /tmp/docker.tgz \
    && mv /tmp/docker/docker /usr/local/bin/docker \
    && chmod +x /usr/local/bin/docker \
    && rm -rf /tmp/docker /tmp/docker.tgz \
    && docker --version

# Install docker-compose (standalone binary)
RUN curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-linux-x86_64" -o /usr/local/bin/docker-compose \
    && chmod +x /usr/local/bin/docker-compose \
    && docker-compose --version

# Setup backend
WORKDIR /app
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy scanner code (worker needs discovery/assets)
COPY scanner/ /app/scanner/

# Copy compiled reporting artifacts
COPY --from=reporting-build /app/scanner/reporting /app/scanner/reporting

# Copy backend
COPY backend/app/ ./app/

# Create non-root user (UID 1000, matches scanner user)
RUN groupadd -g 1000 backend 2>/dev/null || true && \
    useradd -m -u 1000 -g 1000 -s /bin/bash backend && \
    chown -R backend:backend /app

# Create directory for potential temp files (owned by backend)
RUN mkdir -p /tmp/backend && chown backend:backend /tmp/backend

# Copy entrypoint script
COPY frontend/docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

WORKDIR /app

# Expose port (uvicorn can bind to ports >1024 as non-root)
EXPOSE 8080

# Use entrypoint to dynamically configure docker group access
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]

# Run application as non-root user (entrypoint will switch to backend)
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/app
ENV SCANNER_ROOT=/app/scanner
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080", "--no-access-log"]