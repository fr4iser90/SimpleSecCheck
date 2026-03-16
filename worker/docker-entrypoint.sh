#!/bin/bash
# Don't use set -e - we want to continue even if some setup steps fail
set +e

# =========================
# Worker EntryPoint Script
# =========================

# 1️⃣ UID/GID Mapping - Automatically detect from mounted project root directory
# Uses /project mount (from docker-compose: .:/project:ro) to detect host UID/GID
# This ensures files written to ./results have correct ownership on host

WORKER_UID=""
WORKER_GID=""

# Try to detect from mounted /project directory (always available in docker-compose)
if [ -d "/project" ]; then
    DETECTED_UID=$(stat -c "%u" "/project" 2>/dev/null || echo "")
    DETECTED_GID=$(stat -c "%g" "/project" 2>/dev/null || echo "")
    if [ -n "$DETECTED_UID" ] && [ -n "$DETECTED_GID" ]; then
        WORKER_UID=$DETECTED_UID
        WORKER_GID=$DETECTED_GID
        echo "[Entrypoint] Auto-detected UID=$WORKER_UID GID=$WORKER_GID from /project mount"
        
        CURRENT_UID=$(id -u worker)
        CURRENT_GID=$(id -g worker)
        
        # Only remap if different
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
    else
        echo "[Entrypoint] Could not detect UID/GID from /project, using default worker user"
    fi
else
    # /project not mounted - use default worker user (1000:1000)
    echo "[Entrypoint] /project not mounted, using default worker user (UID/GID from image)"
fi

# =========================
# 2️⃣ Ensure Results Directory
# =========================
RESULTS_DIR=${RESULTS_DIR:-/app/results}
mkdir -p "$RESULTS_DIR"

# Get final UID/GID after remapping (if any)
FINAL_UID=$(id -u worker)
FINAL_GID=$(id -g worker)

# Only set ownership once with correct UID/GID
echo "[Entrypoint] Setting ownership for $RESULTS_DIR to UID=$FINAL_UID GID=$FINAL_GID"
chown -R "$FINAL_UID:$FINAL_GID" "$RESULTS_DIR" 2>/dev/null || true
chmod -R u+rwX,g+rwX "$RESULTS_DIR" 2>/dev/null || true

if ! gosu worker test -w "$RESULTS_DIR"; then
    echo "[Entrypoint] WARNING: $RESULTS_DIR not writable by worker"
    ls -ld "$RESULTS_DIR" || true
fi

# =========================
# 3️⃣ Docker Socket (optional)
# =========================
# Worker needs Docker socket to create scanner containers dynamically
# Create or update docker group with correct GID, add worker user to it
if [ -S /var/run/docker.sock ]; then
    DOCKER_GID=$(stat -c "%g" /var/run/docker.sock)
    echo "[Entrypoint] Docker socket GID: $DOCKER_GID"

    # Find existing group with this GID
    DOCKER_GROUP_NAME=$(getent group "$DOCKER_GID" | cut -d: -f1)
    
    if [ -z "$DOCKER_GROUP_NAME" ]; then
        # No group with this GID exists - check if docker group exists with wrong GID
        if getent group docker > /dev/null 2>&1; then
            # Docker group exists but has wrong GID - change it to match socket
            CURRENT_DOCKER_GID=$(getent group docker | cut -d: -f3)
            if [ "$CURRENT_DOCKER_GID" != "$DOCKER_GID" ]; then
                echo "[Entrypoint] Docker group exists with GID $CURRENT_DOCKER_GID, changing to $DOCKER_GID"
                groupmod -g "$DOCKER_GID" docker 2>/dev/null || {
                    echo "[Entrypoint] Warning: Could not change docker group GID to $DOCKER_GID"
                }
            fi
            DOCKER_GROUP_NAME=docker
        else
            # No docker group exists - create it with correct GID
            if groupadd -g "$DOCKER_GID" docker 2>/dev/null; then
                DOCKER_GROUP_NAME=docker
                echo "[Entrypoint] Created docker group with GID $DOCKER_GID"
            else
                echo "[Entrypoint] Warning: Could not create docker group with GID $DOCKER_GID"
            fi
        fi
    else
        echo "[Entrypoint] Found existing group '$DOCKER_GROUP_NAME' with GID $DOCKER_GID"
    fi

    # Add worker user to the group if group exists and user is not already a member
    if [ -n "$DOCKER_GROUP_NAME" ] && ! id -nG worker | grep -qw "$DOCKER_GROUP_NAME"; then
        echo "[Entrypoint] Adding worker user to group $DOCKER_GROUP_NAME"
        usermod -aG "$DOCKER_GROUP_NAME" worker
    fi
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