FROM python:3.13-slim

# Minimal Dependencies + Build tools for asyncpg (C extensions)
RUN apt-get update && apt-get install -y \
    curl \
    git \
    gosu \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Docker CLI 
RUN curl -L "https://download.docker.com/linux/static/stable/x86_64/docker-26.1.4.tgz" -o /tmp/docker.tgz \
    && tar -xz -C /tmp -f /tmp/docker.tgz \
    && mv /tmp/docker/docker /usr/local/bin/docker \
    && chmod +x /usr/local/bin/docker \
    && rm -rf /tmp/docker /tmp/docker.tgz \
    && docker --version

# Python Dependencies
WORKDIR /app
COPY worker/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Worker code
COPY worker/ /app/worker/

# Create docker group and non-root user
RUN groupadd -g 999 docker || true && \
    groupadd -g 1000 worker || true && \
    useradd -m -u 1000 -g 1000 -G docker worker || true && \
    chown -R worker:worker /app

# Entrypoint for dynamic UID/GID and docker group
COPY worker/docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Security: process runs as non-root user "worker" via entrypoint (gosu).
# USER is not set so entrypoint can run as root to set docker group and UID/GID, then exec gosu worker.
WORKDIR /app

# Env defaults
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/app
ENV RESULTS_DIR=/app/results

# Entrypoint & CMD - Entrypoint runs as root, then switches to worker user
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
CMD ["python", "worker/cli/worker_main.py"]
