#!/bin/sh

# Exit immediately if a command exits with a non-zero status.
set -e

# Function to check if PostgreSQL is ready
wait_for_postgres() {
  echo "Waiting for PostgreSQL to be ready..."
  if [ -z "$DB_HOST" ] || [ -z "$DB_USER" ] || [ -z "$DB_NAME" ] || [ -z "$DB_PASSWORD" ]; then
    echo "FATAL: Database connection parameters (DB_HOST, DB_USER, DB_NAME, DB_PASSWORD) are not fully set."
    echo "DB_HOST: $DB_HOST, DB_USER: $DB_USER, DB_NAME: $DB_NAME, PGPASSWORD_SET: $([ -n "$DB_PASSWORD" ] && echo true || echo false)"
    exit 1
  fi
  export PGPASSWORD="$DB_PASSWORD" # Ensure PGPASSWORD is set for psql
  # Loop until psql can connect and execute a simple query (\q) - REMOVED 2>/dev/null for verbose errors
  until psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -c '\q'; do
    echo "PostgreSQL is unavailable (Host: $DB_HOST, User: $DB_USER, DB: $DB_NAME) - sleeping - psql error above if any"
    sleep 1
  done
  unset PGPASSWORD # Unset PGPASSWORD after use for security
  echo "PostgreSQL is up - executing command"
}

# Determine the command to run based on the first argument passed to the script
# This allows the same entrypoint to be used for Gunicorn, Celery worker, Celery beat, etc.
case "$1" in
  "gunicorn")
    echo "Starting Gunicorn server..."
    # Wait for DB only if it's the Gunicorn server (which might need DB for startup/migrations)
    if [ "${WAIT_FOR_DB:-true}" = "true" ]; then
      wait_for_postgres
    fi
    
    echo "Applying database migrations..."
    poetry run python manage.py migrate --noinput

    echo "Collecting static files..."
    poetry run python manage.py collectstatic --noinput --clear
    # chown -R appuser:appuser /app/staticfiles_collected # If using non-root user
    # chown -R appuser:appuser /app/media # If using non-root user
    ;;
  "celery_worker")
    echo "Starting Celery worker..."
    # Celery workers also might need DB to be ready if they interact with Django ORM on startup or for specific tasks.
    if [ "${WAIT_FOR_DB_CELERY:-true}" = "true" ]; then
      wait_for_postgres
    fi
    # The command for celery worker is passed as "celery_worker" then the actual celery command
    # We shift to remove "celery_worker" and then execute the rest.
    shift
    ;; # The actual celery command is executed by "exec" below
  "celery_beat")
    echo "Starting Celery beat..."
    # Celery beat might need DB for DatabaseScheduler.
    if [ "${WAIT_FOR_DB_CELERY_BEAT:-true}" = "true" ]; then
      wait_for_postgres
    fi
    # Similar to worker, shift and execute the rest.
    shift
    ;; # The actual celery beat command is executed by "exec" below
  *) 
    # If no specific known command, just run what was passed.
    # This allows running arbitrary commands like `poetry run python manage.py shell`
    echo "Running command as is: $@"
    ;;
esac

# Execute the command passed into the Docker container (e.g., Gunicorn, Celery command, or manage.py command)
# `exec "$@"` replaces the shell process with the command, so signals are passed correctly.
exec "$@" 