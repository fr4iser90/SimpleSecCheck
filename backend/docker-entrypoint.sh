#!/bin/bash
# Backend Refactored Docker Entrypoint

set -e
# Optionally remap backend user/group to host UID/GID for volume permissions
PUID=${PUID:-1000}
PGID=${PGID:-1000}
echo "[Entrypoint] Requested PUID=$PUID PGID=$PGID"
CURRENT_UID=$(id -u backend)
CURRENT_GID=$(id -g backend)

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