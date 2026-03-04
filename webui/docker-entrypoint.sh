#!/bin/bash
set -e

# Optionally remap webui user/group to host UID/GID for volume permissions
PUID=${PUID:-1000}
PGID=${PGID:-1000}
echo "[Entrypoint] Requested PUID=$PUID PGID=$PGID"
CURRENT_UID=$(id -u webui)
CURRENT_GID=$(id -g webui)

if [ "$PGID" != "$CURRENT_GID" ]; then
    if getent group "$PGID" >/dev/null 2>&1; then
        usermod -g "$PGID" webui
    else
        groupmod -g "$PGID" webui
    fi
fi

if [ "$PUID" != "$CURRENT_UID" ]; then
    usermod -u "$PUID" webui
fi

CHOWN_UID=$(id -u webui)
CHOWN_GID=$(id -g webui)

# Ensure results directory exists and is writable by webui
RESULTS_DIR=${RESULTS_DIR:-/app/results}
if [ ! -d "$RESULTS_DIR" ]; then
    echo "[Entrypoint] Creating results directory at $RESULTS_DIR"
    mkdir -p "$RESULTS_DIR"
fi
echo "[Entrypoint] Ensuring ownership for $RESULTS_DIR (uid=$CHOWN_UID gid=$CHOWN_GID)"
chown -R "$CHOWN_UID:$CHOWN_GID" "$RESULTS_DIR" 2>/dev/null || true
chmod -R u+rwX,g+rwX "$RESULTS_DIR" 2>/dev/null || true

if ! gosu webui test -w "$RESULTS_DIR"; then
    echo "[Entrypoint] WARNING: $RESULTS_DIR is still not writable by webui (uid=$CHOWN_UID gid=$CHOWN_GID)"
    ls -ld "$RESULTS_DIR" || true
fi

# Dynamically determine Docker socket GID and add webui user to docker group
# This works across different systems where the docker socket GID may vary
if [ -S /var/run/docker.sock ]; then
    DOCKER_GID=$(stat -c "%g" /var/run/docker.sock)
    echo "[Entrypoint] Docker socket GID: $DOCKER_GID"

    # Resolve or create a group with the Docker socket GID
    DOCKER_GROUP_NAME=$(getent group "$DOCKER_GID" | cut -d: -f1)
    if [ -z "$DOCKER_GROUP_NAME" ]; then
        if getent group docker > /dev/null 2>&1; then
            DOCKER_GROUP_NAME=docker
        else
            echo "[Entrypoint] Creating docker group with GID $DOCKER_GID"
            if groupadd -g "$DOCKER_GID" docker 2>/dev/null; then
                DOCKER_GROUP_NAME=docker
            else
                echo "[Entrypoint] Warning: Could not create docker group with GID $DOCKER_GID"
            fi
        fi
    fi

    # Add webui user to the resolved group (if any)
    if [ -n "$DOCKER_GROUP_NAME" ] && ! id -nG webui | grep -qw "$DOCKER_GROUP_NAME"; then
        echo "[Entrypoint] Adding webui user to group $DOCKER_GROUP_NAME"
        usermod -aG "$DOCKER_GROUP_NAME" webui
    elif [ -z "$DOCKER_GROUP_NAME" ]; then
        echo "[Entrypoint] Warning: Docker group not available, skipping usermod"
    fi
else
    echo "[Entrypoint] Warning: Docker socket not found at /var/run/docker.sock"
fi

# Switch to webui user and execute the command
exec gosu webui "$@"
