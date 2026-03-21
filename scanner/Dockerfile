# Stage 1: Main scanner image
FROM ubuntu:22.04

# Version information
ARG VERSION=2.0.0
LABEL version=$VERSION
LABEL maintainer="fr4iser"

## Core dependencies are now installed via scanner manifests (Option B modular build).
## Minimal runtime installs Python + PyYAML to read manifests and Node.js for report build.
RUN apt-get update && \
    apt-get install -y python3 python3-pip curl gosu git && \
    pip3 install pyyaml && \
    curl -fsSL https://deb.nodesource.com/setup_22.x | bash - && \
    apt-get install -y nodejs

## Scanner tool installations moved into per-module manifests

# Copy only scanner manifests + asset installer first to improve build cache reuse
COPY scanner/core/scanner_assets/ /app/scanner/core/scanner_assets/
COPY scanner/plugins/ /app/scanner/plugins/
WORKDIR /app

RUN mkdir -p /app/results

# Run module installers declared via manifests (cached unless manifests change)
ENV SIMPLE_SECCHECK_ROOT=/app
RUN python3 -m scanner.core.scanner_assets.install_assets

# Copy full SimpleSecCheck files after assets install
COPY scanner/ /app/scanner/

# Copy entrypoint script
COPY scanner/docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Create non-root user (UID/GID will be set dynamically via PUID/PGID env vars in entrypoint)
RUN useradd -m -s /bin/bash scanner && \
    chown -R scanner:scanner /app /home/scanner

# Make scripts executable
RUN chmod +x /app/scanner/core/configure.py

# Install TypeScript dependencies and compile TypeScript files
RUN cd /app/scanner/output && npm install && npx tsc

# Install sudo and configure passwordless sudo for scanner user
RUN apt-get install -y sudo && \
    echo 'scanner ALL=(ALL) NOPASSWD: ALL' >> /etc/sudoers

# Ensure writable home/cache locations for CLI tools (generic)
ENV HOME=/tmp/scanner
ENV XDG_CACHE_HOME=/tmp/scanner/.cache
ENV XDG_CONFIG_HOME=/tmp/scanner/.config
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Security: process runs as non-root user "scanner" via entrypoint (gosu).
# USER is not set so entrypoint can run as root to set volume permissions and UID/GID, then exec gosu scanner.

# Ensure scanner modules are importable regardless of working directory
ENV PYTHONPATH=/app
ENV SCANNER_ROOT=/app/scanner

WORKDIR /app
# Use entrypoint to dynamically configure docker group access
# Entrypoint runs as root, then switches to scanner user
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
CMD ["python3", "-m", "scanner.core.orchestrator"]