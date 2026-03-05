# Stage 1: Main scanner image
FROM ubuntu:22.04

# Version information
ARG VERSION=1.4.0
LABEL version=$VERSION
LABEL maintainer="fr4iser"

## Core dependencies are now installed via scanner manifests (Option B modular build).
## Minimal runtime installs Python + PyYAML to read manifests and Node.js for report build.
RUN apt-get update && \
    apt-get install -y python3 python3-pip curl && \
    pip3 install pyyaml && \
    curl -fsSL https://deb.nodesource.com/setup_18.x | bash - && \
    apt-get install -y nodejs

## Scanner tool installations moved into per-module manifests

# Copy only scanner manifests + asset installer first to improve build cache reuse
COPY scanner/core/scanner_assets/ /SimpleSecCheck/scanner/core/scanner_assets/
COPY scanner/scanners/ /SimpleSecCheck/scanner/scanners/
WORKDIR /SimpleSecCheck

RUN mkdir -p /SimpleSecCheck/results

# Run module installers declared via manifests (cached unless manifests change)
ENV SIMPLE_SECCHECK_ROOT=/SimpleSecCheck
RUN python3 -m scanner.core.scanner_assets.install_assets

# Copy full SimpleSecCheck files (scanner code and entrypoint) after assets install
COPY scanner/ /SimpleSecCheck/scanner/
COPY entrypoint.sh /entrypoint.sh

# Create non-root user (1000:1000 matches typical host user)
RUN useradd -m -u 1000 -s /bin/bash scanner && \
    (groupadd -g 999 docker || true) && \
    usermod -aG docker scanner && \
    chown -R scanner:scanner /SimpleSecCheck /home/scanner

# Make scripts executable
RUN chmod +x /SimpleSecCheck/scanner/core/configure.py

# Compile TypeScript files (uses tsconfig.json automatically)
RUN cd /SimpleSecCheck/scanner/reporting && tsc

# Install sudo and configure passwordless sudo for scanner user
RUN apt-get install -y sudo && \
    echo 'scanner ALL=(ALL) NOPASSWD: ALL' >> /etc/sudoers

# Set up entrypoint script permissions
RUN chmod +x /entrypoint.sh

# Ensure writable home/cache locations for CLI tools (generic)
ENV HOME=/tmp/scanner
ENV XDG_CACHE_HOME=/tmp/scanner/.cache
ENV XDG_CONFIG_HOME=/tmp/scanner/.config

# Switch to non-root user
USER scanner

# Ensure scanner modules are importable regardless of working directory
ENV PYTHONPATH=/SimpleSecCheck

WORKDIR /SimpleSecCheck
ENTRYPOINT ["/entrypoint.sh"]
CMD ["python3", "-m", "scanner.core.orchestrator"]