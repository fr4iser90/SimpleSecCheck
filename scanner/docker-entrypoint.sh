#!/bin/bash
# Don't use set -e here - we want to continue even if some setup steps fail
# The actual command execution will handle its own errors
set +e

# Optionally remap scanner user/group to host UID/GID for volume permissions
PUID=${PUID:-1000}
PGID=${PGID:-1000}
echo "[Entrypoint] Requested PUID=$PUID PGID=$PGID"
CURRENT_UID=$(id -u scanner)
CURRENT_GID=$(id -g scanner)

if [ "$PGID" != "$CURRENT_GID" ]; then
    if getent group "$PGID" >/dev/null 2>&1; then
        usermod -g "$PGID" scanner
    else
        groupmod -g "$PGID" scanner
    fi
fi

if [ "$PUID" != "$CURRENT_UID" ]; then
    usermod -u "$PUID" scanner
fi

CHOWN_UID=$(id -u scanner)
CHOWN_GID=$(id -g scanner)

# Ensure results directory exists and is writable by scanner
RESULTS_DIR=${RESULTS_DIR_IN_CONTAINER:-/app/results}
if [ ! -d "$RESULTS_DIR" ]; then
    echo "[Entrypoint] Creating results directory at $RESULTS_DIR"
    mkdir -p "$RESULTS_DIR"
fi
echo "[Entrypoint] Ensuring ownership for $RESULTS_DIR (uid=$CHOWN_UID gid=$CHOWN_GID)"
chown -R "$CHOWN_UID:$CHOWN_GID" "$RESULTS_DIR" 2>/dev/null || true
chmod -R u+rwX,g+rwX "$RESULTS_DIR" 2>/dev/null || true

if ! gosu scanner test -w "$RESULTS_DIR"; then
    echo "[Entrypoint] WARNING: $RESULTS_DIR is still not writable by scanner (uid=$CHOWN_UID gid=$CHOWN_GID)"
    ls -ld "$RESULTS_DIR" || true
fi

# Dynamically determine Docker socket GID and add scanner user to docker group
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

    # Add scanner user to the resolved group (if any)
    if [ -n "$DOCKER_GROUP_NAME" ] && ! id -nG scanner | grep -qw "$DOCKER_GROUP_NAME"; then
        echo "[Entrypoint] Adding scanner user to group $DOCKER_GROUP_NAME"
        usermod -aG "$DOCKER_GROUP_NAME" scanner
    elif [ -z "$DOCKER_GROUP_NAME" ]; then
        echo "[Entrypoint] Warning: Docker group not available, skipping usermod"
    fi
else
    echo "[Entrypoint] Warning: Docker socket not found at /var/run/docker.sock"
fi

# Ensure mounted volumes exist and are writable by scanner
RESULTS_DIR="${RESULTS_DIR_IN_CONTAINER:-/app/results}"
LOGS_DIR="${LOGS_DIR_IN_CONTAINER:-${RESULTS_DIR}/logs}"
TARGET_DIR="${TARGET_PATH_IN_CONTAINER:-/target}"
HOME_DIR="${HOME:-/tmp/scanner}"
CACHE_DIR="${XDG_CACHE_HOME:-$HOME_DIR/.cache}"
CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME_DIR/.config}"

mkdir -p "$HOME_DIR" "$CACHE_DIR" "$CONFIG_DIR" || true

mkdir -p "$RESULTS_DIR" "$LOGS_DIR"
chmod -R u+rwX,g+rwX "$RESULTS_DIR" "$LOGS_DIR" 2>/dev/null || true

if ! test -w "$RESULTS_DIR"; then
    echo "[Entrypoint] WARNING: $RESULTS_DIR is not writable by current user (uid=$(id -u) gid=$(id -g))"
    ls -ld "$RESULTS_DIR" || true
fi

if ! test -w "$LOGS_DIR"; then
    echo "[Entrypoint] WARNING: $LOGS_DIR is not writable by current user (uid=$(id -u) gid=$(id -g))"
    ls -ld "$LOGS_DIR" || true
fi

if ! test -w "$HOME_DIR"; then
    echo "[Entrypoint] WARNING: $HOME_DIR is not writable by current user (uid=$(id -u) gid=$(id -g))"
    ls -ld "$HOME_DIR" || true
fi

if ! test -d "$TARGET_DIR"; then
    echo "[Entrypoint] WARNING: Target directory $TARGET_DIR is missing. Ensure /target is mounted correctly."
    ls -ld "/target" || true
else
    echo "[Entrypoint] Target directory available at $TARGET_DIR"
fi


# Switch to scanner user and execute the command
# Use exec to replace shell process and preserve exit code
exec "$@"
