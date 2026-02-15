#!/bin/bash
set -e

# Dynamically determine Docker socket GID and add webui user to docker group
# This works across different systems where the docker socket GID may vary
if [ -S /var/run/docker.sock ]; then
    DOCKER_GID=$(stat -c "%g" /var/run/docker.sock)
    echo "[Entrypoint] Docker socket GID: $DOCKER_GID"
    
    # Create docker group with the detected GID (if it doesn't exist)
    if ! getent group docker > /dev/null 2>&1; then
        echo "[Entrypoint] Creating docker group with GID $DOCKER_GID"
        groupadd -g "$DOCKER_GID" docker 2>/dev/null || true
    fi
    
    # Add webui user to docker group (if not already a member)
    if ! id -nG webui | grep -qw docker; then
        echo "[Entrypoint] Adding webui user to docker group"
        usermod -aG docker webui
    fi
else
    echo "[Entrypoint] Warning: Docker socket not found at /var/run/docker.sock"
fi

# Switch to webui user and execute the command
exec gosu webui "$@"
