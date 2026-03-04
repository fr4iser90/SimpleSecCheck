#!/bin/bash
set -e

# Ensure mounted volumes exist and are writable by scanner
RESULTS_DIR="${RESULTS_DIR_IN_CONTAINER:-/SimpleSecCheck/results}"
LOGS_DIR="${LOGS_DIR_IN_CONTAINER:-/SimpleSecCheck/results/logs}"
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

# Run the command passed as arguments
exec "$@"

