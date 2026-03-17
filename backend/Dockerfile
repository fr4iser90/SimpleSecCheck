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
    && rm -rf /var/lib/apt/lists/*

# Download ClamAV virus DB at build
RUN mkdir -p /var/lib/clamav \
    && freshclam --quiet || true \
    && chmod -R 755 /var/lib/clamav

# Copy requirements and install Python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY backend/ /app/backend/

# Create non-root user
RUN groupadd -r backend && useradd -r -g backend backend
RUN chown -R backend:backend /app
USER backend

# Expose port
EXPOSE 8080

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/app/backend

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8080/api/health', timeout=5)"

# Start command
CMD ["sh", "-c", "uvicorn api.main:app --host 0.0.0.0 --port 8080"]

