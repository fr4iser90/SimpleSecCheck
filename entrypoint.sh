#!/bin/bash
set -e

# Ensure mounted volumes exist and are writable by scanner
RESULTS_DIR="/SimpleSecCheck/results"
LOGS_DIR="/SimpleSecCheck/logs"

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

# Run the command passed as arguments
exec "$@"

