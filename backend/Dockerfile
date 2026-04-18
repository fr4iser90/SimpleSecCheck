# Backend Refactored Dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    git \
    clamav \
    clamav-freshclam \
    gosu \
    && rm -rf /var/lib/apt/lists/*

# Download ClamAV virus DB at build
RUN mkdir -p /var/lib/clamav \
    && freshclam --quiet || true \
    && chmod -R 755 /var/lib/clamav \
    && chmod -R o+rX /var/lib/clamav

# Copy requirements and install Python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY backend/ /app/backend/

# Non-root user; UID/GID matched to host via docker-entrypoint.sh (/project mount)
RUN groupadd -r backend && useradd -r -g backend backend
RUN chown -R backend:backend /app
COPY backend/docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh
# Run as root until entrypoint maps backend user and exec gosu (same as worker/scanner)
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]

# Expose port
EXPOSE 8080

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/app/backend

# Health check (run as backend after gosu; use same python as app)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD gosu backend python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/api/health', timeout=5)"

# Start command
# Trust X-Forwarded-Proto from nginx/Traefik so redirects use https:// in Location
CMD ["sh", "-c", "uvicorn api.main:app --host 0.0.0.0 --port 8080 --proxy-headers --forwarded-allow-ips='*'"]

