#!/bin/sh
set -e

# Optionally remap nginx user/group to host UID/GID for volume permissions
PUID=${PUID:-1000}
PGID=${PGID:-1000}
CURRENT_UID=$(id -u nginx 2>/dev/null || echo 101)
CURRENT_GID=$(id -g nginx 2>/dev/null || echo 101)

if [ "$PGID" != "$CURRENT_GID" ]; then
    if getent group "$PGID" >/dev/null 2>&1; then
        usermod -g "$PGID" nginx >/dev/null 2>&1 || true
    else
        groupmod -g "$PGID" nginx >/dev/null 2>&1 || true
    fi
fi

if [ "$PUID" != "$CURRENT_UID" ]; then
    usermod -u "$PUID" nginx >/dev/null 2>&1 || true
fi

CHOWN_UID=$(id -u nginx 2>/dev/null || echo 101)
CHOWN_GID=$(id -g nginx 2>/dev/null || echo 101)

# Ensure results directory exists and is readable by nginx
RESULTS_DIR=${RESULTS_DIR:-/app/results}
if [ ! -d "$RESULTS_DIR" ]; then
    mkdir -p "$RESULTS_DIR" >/dev/null 2>&1 || true
fi
chown -R "$CHOWN_UID:$CHOWN_GID" "$RESULTS_DIR" 2>/dev/null || true
chmod -R u+rX,g+rX "$RESULTS_DIR" 2>/dev/null || true

# Backup and use standard entrypoint, but suppress output
if [ -f /usr/local/bin/docker-entrypoint.sh ]; then
    # Execute standard entrypoint scripts silently
    if [ -d /docker-entrypoint.d ]; then
        for f in /docker-entrypoint.d/*.sh; do
            [ -f "$f" ] && . "$f" >/dev/null 2>&1 || true
        done
    fi
fi

# Show only our message
echo "nginx started"

# Start nginx in foreground, suppress ALL output (stdout and stderr)
exec nginx -g "daemon off; error_log /dev/null crit;" >/dev/null 2>&1
