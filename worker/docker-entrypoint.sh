#!/bin/bash
# Don't use set -e - we want to continue even if some setup steps fail
set +e

# =========================
# Worker EntryPoint Script
# =========================

# 1️⃣ UID/GID Mapping
WORKER_UID=${PUID:-1000}
WORKER_GID=${PGID:-1000}

echo "[Entrypoint] Requested UID=$WORKER_UID GID=$WORKER_GID"

CURRENT_UID=$(id -u worker)
CURRENT_GID=$(id -g worker)

if [ "$WORKER_GID" != "$CURRENT_GID" ]; then
    if getent group "$WORKER_GID" >/dev/null 2>&1; then
        usermod -g "$WORKER_GID" worker
    else
        groupmod -g "$WORKER_GID" worker
    fi
fi

if [ "$WORKER_UID" != "$CURRENT_UID" ]; then
    usermod -u "$WORKER_UID" worker
fi

# =========================
# 2️⃣ Ensure Results Directory
# =========================
RESULTS_DIR=${RESULTS_DIR:-/app/results}
mkdir -p "$RESULTS_DIR"

CHOWN_UID=$(id -u worker)
CHOWN_GID=$(id -g worker)

echo "[Entrypoint] Setting ownership for $RESULTS_DIR to UID=$CHOWN_UID GID=$CHOWN_GID"
chown -R "$CHOWN_UID:$CHOWN_GID" "$RESULTS_DIR" 2>/dev/null || true
chmod -R u+rwX,g+rwX "$RESULTS_DIR" 2>/dev/null || true

if ! gosu worker test -w "$RESULTS_DIR"; then
    echo "[Entrypoint] WARNING: $RESULTS_DIR not writable by worker"
    ls -ld "$RESULTS_DIR" || true
fi

# =========================
# 3️⃣ Docker Socket (optional)
# =========================
if [ -S /var/run/docker.sock ]; then
    DOCKER_GID=$(stat -c "%g" /var/run/docker.sock)
    echo "[Entrypoint] Docker socket GID: $DOCKER_GID"

    # Resolve or create a group with the Docker socket GID
    DOCKER_GROUP_NAME=$(getent group "$DOCKER_GID" | cut -d: -f1)
    if [ -z "$DOCKER_GROUP_NAME" ]; then
        # No group with this GID exists, check if docker group exists
        if getent group docker > /dev/null 2>&1; then
            # Docker group exists but has wrong GID - change it
            echo "[Entrypoint] Docker group exists with different GID, changing to $DOCKER_GID"
            groupmod -g "$DOCKER_GID" docker 2>/dev/null || true
            DOCKER_GROUP_NAME=docker
        else
            # Create new docker group with correct GID
            echo "[Entrypoint] Creating docker group with GID $DOCKER_GID"
            if groupadd -g "$DOCKER_GID" docker 2>/dev/null; then
                DOCKER_GROUP_NAME=docker
            else
                echo "[Entrypoint] Warning: Could not create docker group with GID $DOCKER_GID"
            fi
        fi
    else
        echo "[Entrypoint] Found existing group '$DOCKER_GROUP_NAME' with GID $DOCKER_GID"
    fi

    # Add worker user to the resolved group (if any)
    # Entrypoint runs as root, so we can directly use usermod
    if [ -n "$DOCKER_GROUP_NAME" ] && ! id -nG worker | grep -qw "$DOCKER_GROUP_NAME"; then
        echo "[Entrypoint] Adding worker user to group $DOCKER_GROUP_NAME"
        usermod -aG "$DOCKER_GROUP_NAME" worker
    elif [ -z "$DOCKER_GROUP_NAME" ]; then
        echo "[Entrypoint] Warning: Docker group not available, skipping usermod"
    fi
    
    # Ensure worker can access the docker socket (optional, group membership should be enough)
    chmod 666 /var/run/docker.sock 2>/dev/null || true
else
    echo "[Entrypoint] Docker socket not found, skipping docker group setup"
fi

# =========================
# 4️⃣ Drop privileges and execute CMD as worker user
# =========================
# Entrypoint runs as root to configure Docker group
# Now drop privileges to worker user using gosu (standard pattern)
# This is the secure way: root setup, then non-root execution
exec gosu worker "$@"