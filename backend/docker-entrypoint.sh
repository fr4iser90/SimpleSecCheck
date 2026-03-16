#!/bin/bash
# Backend Refactored Docker Entrypoint

set -e
# Automatically detect UID/GID from mounted project root directory
# This ensures files are created with correct ownership on host
# /project is always mounted in docker-compose (.:/project:ro)

PROJECT_ROOT="/project"
if [ -d "$PROJECT_ROOT" ]; then
    DETECTED_UID=$(stat -c "%u" "$PROJECT_ROOT" 2>/dev/null || echo "")
    DETECTED_GID=$(stat -c "%g" "$PROJECT_ROOT" 2>/dev/null || echo "")
    if [ -n "$DETECTED_UID" ] && [ -n "$DETECTED_GID" ]; then
        PUID=$DETECTED_UID
        PGID=$DETECTED_GID
        echo "[Entrypoint] Auto-detected PUID=$PUID PGID=$PGID from $PROJECT_ROOT"
    else
        echo "[Entrypoint] Could not detect UID/GID from $PROJECT_ROOT, skipping user remapping"
    fi
else
    echo "[Entrypoint] Project root $PROJECT_ROOT not found, skipping user remapping"
fi

CURRENT_UID=$(id -u backend)
CURRENT_GID=$(id -g backend)

# Only remap if PUID/PGID were detected
if [ -n "$PUID" ] && [ -n "$PGID" ]; then
    if [ "$PGID" != "$CURRENT_GID" ]; then
        if getent group "$PGID" >/dev/null 2>&1; then
            usermod -g "$PGID" backend
        else
            groupmod -g "$PGID" backend
        fi
    fi

    if [ "$PUID" != "$CURRENT_UID" ]; then
        usermod -u "$PUID" backend
    fi
fi

CHOWN_UID=$(id -u backend)
CHOWN_GID=$(id -g backend) 

# Wait for dependencies
echo "Waiting for database and Redis..."
until pg_isready -h "$DATABASE_HOST" -p "$DATABASE_PORT" -U "$DATABASE_USER" 2>/dev/null; do
  echo "Waiting for database..."
  sleep 2
done

until redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" ping 2>/dev/null; do
  echo "Waiting for Redis..."
  sleep 2
done

echo "Dependencies are ready!"

# Run migrations if needed
if [ "$RUN_MIGRATIONS" = "true" ]; then
  echo "Running database migrations..."
  # Add migration commands here
fi

# Start the application
echo "Starting backend application..."
exec "$@"