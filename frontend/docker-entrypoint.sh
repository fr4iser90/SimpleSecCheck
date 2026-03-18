#!/bin/sh
set -e

# Do NOT chown ./results here. Backend/Worker/Scanner map to host UID (e.g. 1000:992).
# If usermod for nginx fails, chown -R would reassign the whole tree to nginx (UID 101)
# and break scanner writes — that caused intermittent 101 vs fr4iser on the host.

# Optional mount; nginx does not read results (API proxies to backend). No chown/chmod.
RESULTS_DIR=${RESULTS_DIR:-/app/results}
[ -d "$RESULTS_DIR" ] || mkdir -p "$RESULTS_DIR" 2>/dev/null || true

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
