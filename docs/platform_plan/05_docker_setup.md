# SecuLite v2 - Docker Setup Plan

This document details the Docker setup for SecuLite v2, including the services, Dockerfiles, `docker-compose.yml` configuration, and environment variables. The goal is to create a reproducible and consistent development, testing, and production-like environment.

## Table of Contents

1.  [Overview of Services](#1-overview-of-services)
2.  [Core File Structure (Related to Docker)](#2-core-file-structure-related-to-docker)
3.  [`docker-compose.yml` Structure and Service Definitions](#3-docker-composeyml-structure-and-service-definitions)
    *   [3.1. `db` (PostgreSQL) Service](#31-db-postgresql-service)
    *   [3.2. `redis` Service](#32-redis-service)
    *   [3.3. `backend` (Django) Service](#33-backend-django-service)
    *   [3.4. `worker` (Celery Worker) Service](#34-worker-celery-worker-service)
    *   [3.5. `beat` (Celery Beat) Service](#35-beat-celery-beat-service)
    *   [3.6. `frontend` (Vue.js Build Stage - in Dockerfile)](#36-frontend-vuejs-build-stage---in-dockerfile)
    *   [3.7. `nginx` (Web Server/Reverse Proxy) Service](#37-nginx-web-serverreverse-proxy-service)
    *   [3.8. Volumes](#38-volumes)
    *   [3.9. Networks](#39-networks)
4.  [`backend/Dockerfile` Details](#4-backenddockerfile-details)
5.  [`backend/entrypoint.sh` Details](#5-backendentrypointsh-details)
6.  [`frontend/Dockerfile` Details (Multi-stage)](#6-frontenddockerfile-details-multi-stage)
7.  [`nginx/nginx.conf` Details (Example for `nginx` service)](#7-nginxnginxconf-details-example-for-nginx-service)
8.  [Environment Variables (`.env.example`)](#8-environment-variables-envexample)
9.  [Development Workflow Considerations](#9-development-workflow-considerations)
10. [Production Deployment Considerations (Brief)](#10-production-deployment-considerations-brief)

---

## 1. Overview of Services

The SecuLite v2 platform will be composed of the following containerized services orchestrated by Docker Compose:

-   **`db`**: PostgreSQL database server for persistent data storage.
-   **`redis`**: Redis in-memory data store, primarily used as a message broker for Celery and potentially for caching.
-   **`backend`**: The Django application serving the REST API. Gunicorn will be used as the WSGI HTTP server.
-   **`worker`**: Celery worker process(es) that execute asynchronous tasks (e.g., running security scans).
-   **`beat`**: Celery beat scheduler process for periodic/scheduled tasks (e.g., daily scans).
-   **`frontend`**: (Build stage) While the Vue.js app is built into static assets, its Dockerfile will handle this build process.
-   **`nginx`**: Nginx web server acting as a reverse proxy. It will serve the static frontend assets (built by Vue.js) and proxy API requests to the Django backend. It can also handle SSL termination in a production-like setup.

---

## 2. Core File Structure (Related to Docker)

Reference `docs/platform_plan/04_project_structure.md` for the full structure. Key files for Docker setup:

```
seculite-v2/
├── backend/
│   ├── Dockerfile
│   └── entrypoint.sh
├── frontend/
│   └── Dockerfile
├── nginx/
│   └── nginx.conf        # Nginx configuration file
│   └── Dockerfile        # Optional: if custom nginx image needed, else use official
├── .dockerignore
├── .env.example
└── docker-compose.yml
```
*(A new `nginx/` directory might be added at the root for Nginx configurations if not embedding in frontend Dockerfile directly)*

---

## 3. `docker-compose.yml` Structure and Service Definitions

*(This section will provide a skeleton of the `docker-compose.yml` file, detailing each service. Actual implementation will fill this out.)*

```yaml
version: '3.8'

services:
  # db (PostgreSQL) Service Definition (Section 3.1)
  # redis Service Definition (Section 3.2)
  # backend (Django) Service Definition (Section 3.3)
  # worker (Celery Worker) Service Definition (Section 3.4)
  # beat (Celery Beat) Service Definition (Section 3.5)
  # nginx (Web Server) Service Definition (Section 3.7)

volumes:
  # Volume definitions (Section 3.8)

networks:
  # Network definitions (Section 3.9)
```

*(Detailed subsections 3.1 to 3.9 will follow, outlining build context, image, volumes, ports, environment variables, depends_on, and networks for each service, plus definitions for named volumes and custom networks.)*

### 3.1. `db` (PostgreSQL) Service
The `db` service will run the PostgreSQL database.

```yaml
services:
  db:
    image: postgres:15-alpine  # Using a specific version of PostgreSQL on Alpine Linux for a smaller image
    container_name: seculite_db
    volumes:
      - postgres_data:/var/lib/postgresql/data  # Persist database data
    env_file:
      - .env  # Load environment variables from .env file (POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB)
    ports:
      - "5432:5432"  # Expose PostgreSQL port to host (primarily for local development/debugging if needed)
    networks:
      - seculite_network
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U $$POSTGRES_USER -d $$POSTGRES_DB"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 10s
```

**Details:**
-   **`image: postgres:15-alpine`**: Specifies the official PostgreSQL image, version 15, based on Alpine Linux for a smaller footprint.
-   **`container_name: seculite_db`**: Assigns a specific name to the container for easier reference.
-   **`volumes: - postgres_data:/var/lib/postgresql/data`**: Mounts a named volume `postgres_data` to persist the database contents across container restarts. This volume will be defined in the top-level `volumes:` section of `docker-compose.yml`.
-   **`env_file: - .env`**: Tells Docker Compose to load environment variables from the `.env` file located in the same directory as `docker-compose.yml`. This file will contain `POSTGRES_USER`, `POSTGRES_PASSWORD`, and `POSTGRES_DB`.
-   **`ports: - "5432:5432"`**: Maps port 5432 of the container to port 5432 on the host machine. This is mainly for local development if direct database access is needed. For security, this might not be exposed externally in production.
-   **`networks: - seculite_network`**: Connects the service to a custom bridge network named `seculite_network`, allowing it to communicate with other services on the same network. This network will be defined in the top-level `networks:` section.
-   **`restart: unless-stopped`**: Ensures the container restarts automatically if it crashes, unless it was explicitly stopped.
-   **`healthcheck`**: Defines a command to check the health of the PostgreSQL server. The backend service will wait for this healthcheck to pass before starting.
    -   `test: ["CMD-SHELL", "pg_isready -U $$POSTGRES_USER -d $$POSTGRES_DB"]`: Runs `pg_isready` to check if the server is accepting connections. Note the use of `$$` to escape `$` for Docker Compose variable interpolation if `POSTGRES_USER` and `POSTGRES_DB` are also set directly in the compose file; if only in `.env`, single `$` is fine for the shell command within the container. For `env_file` sourced variables, the shell inside the container will have them.
    -   `interval`, `timeout`, `retries`, `start_period`: Configure the timing of the healthcheck.

### 3.2. `redis` Service
The `redis` service provides the Redis in-memory data store, used as the Celery message broker.

```yaml
services:
  # ... (db service defined above)
  redis:
    image: redis:7-alpine  # Using a specific version of Redis on Alpine Linux
    container_name: seculite_redis
    volumes:
      - redis_data:/data # Persist Redis data (optional, but good for some setups)
    ports:
      - "6379:6379"  # Expose Redis port to host (primarily for local development/debugging)
    networks:
      - seculite_network
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 5s
```

**Details:**
-   **`image: redis:7-alpine`**: Specifies the official Redis image, version 7, based on Alpine Linux for a smaller size.
-   **`container_name: seculite_redis`**: Assigns a specific name to the Redis container.
-   **`volumes: - redis_data:/data`**: Mounts a named volume `redis_data` to persist Redis data. While Redis is often used as a cache or ephemeral broker, persisting data can be useful for durability in some Celery configurations or if Redis is used for other persistent tasks. This volume will be defined in the top-level `volumes:` section.
-   **`ports: - "6379:6379"`**: Maps port 6379 of the container (default Redis port) to port 6379 on the host. Useful for local development or direct inspection.
-   **`networks: - seculite_network`**: Connects the service to the `seculite_network`.
-   **`restart: unless-stopped`**: Ensures the container restarts if it crashes.
-   **`healthcheck`**: Defines a simple healthcheck for Redis.
    -   `test: ["CMD", "redis-cli", "ping"]`: Uses `redis-cli ping` which should return `PONG` if the server is responsive.
    -   `interval`, `timeout`, `retries`, `start_period`: Configure timing.

### 3.3. `backend` (Django) Service
The `backend` service runs the Django application using Gunicorn as the WSGI server.

```yaml
services:
  # ... (db and redis services defined above)
  backend:
    build:
      context: ./backend  # Path to the backend Dockerfile and related files
      dockerfile: Dockerfile
    container_name: seculite_backend
    entrypoint: /app/entrypoint.sh # Custom entrypoint script (see Section 5)
    command: ["gunicorn", "seculite_api.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "4", "--log-level", "info"]
    volumes:
      - ./backend:/app # Mount backend code for development (live reload)
      - backend_static_collected:/app/staticfiles_collected # Volume for collected static files
      - backend_media_data:/app/media # Volume for user-uploaded media files
    ports:
      - "8000:8000"  # Expose Gunicorn port (mainly for Nginx to proxy to)
    env_file:
      - .env
    depends_on:
      db:
        condition: service_healthy # Wait for db to be healthy
      redis:
        condition: service_healthy # Wait for redis to be healthy
    networks:
      - seculite_network
    restart: unless-stopped
    # No healthcheck here as Gunicorn startup implies health; depends_on handles startup order.
    # If ASGI is used (e.g., with Daphne for Channels), the command would change.
```

**Details:**
-   **`build`**: Specifies how to build the image for this service.
    -   `context: ./backend`: The build context is the `backend` directory.
    -   `dockerfile: Dockerfile`: Uses `backend/Dockerfile` (detailed in Section 4).
-   **`container_name: seculite_backend`**: Specific container name.
-   **`entrypoint: /app/entrypoint.sh`**: Overrides the default entrypoint of the image with our custom script (see Section 5). This script will handle migrations, etc., before starting the main command.
-   **`command: ["gunicorn", "seculite_api.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "4", "--log-level", "info"]`**: The main command to run after the entrypoint. This starts Gunicorn to serve the Django WSGI application (`seculite_api.wsgi:application`).
    -   `--bind 0.0.0.0:8000`: Binds to all network interfaces on port 8000 within the container.
    -   `--workers 4`: Number of Gunicorn worker processes. Adjust based on server resources.
    -   `--log-level info`: Sets Gunicorn log level.
-   **`volumes`**:
    -   `./backend:/app`: Mounts the local `backend` directory into `/app` in the container. This is crucial for development, allowing live code changes without rebuilding the image.
    -   `backend_static_collected:/app/staticfiles_collected`: A named volume for Django's `collectstatic` output. Nginx can potentially serve from this volume.
    -   `backend_media_data:/app/media`: A named volume for user-uploaded files (e.g., `ScanToolResult.raw_output_path`).
-   **`ports: - "8000:8000"`**: Exposes port 8000. While Nginx will be the primary entry point from the outside on port 80/443, this can be useful for direct access during development or if Nginx is on the same host but not in Docker.
-   **`env_file: - .env`**: Loads environment variables from the `.env` file (e.g., `DJANGO_SECRET_KEY`, `DJANGO_DEBUG`, database URL, Celery settings).
-   **`depends_on`**: Ensures that the `db` and `redis` services are healthy before this service starts.
    -   `condition: service_healthy` relies on the `healthcheck` defined in the `db` and `redis` services.
-   **`networks: - seculite_network`**: Connects to the shared network.
-   **`restart: unless-stopped`**: Automatic restart policy.

### 3.4. `worker` (Celery Worker) Service
The `worker` service runs Celery workers to process asynchronous tasks. It uses the same Docker image as the `backend` service but runs a different command.

```yaml
services:
  # ... (db, redis, backend services defined above)
  worker:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: seculite_worker
    command: ["celery", "-A", "seculite_api", "worker", "-l", "info", "-Q", "default,scans", "-c", "2"]
    volumes:
      - ./backend:/app # Mount backend code for development (live reload of tasks)
      - backend_media_data:/app/media # Access to media files if tasks need them
    env_file:
      - .env
    depends_on:
      backend: # Implicitly depends on db and redis through backend
        condition: service_started # Ensures backend (and its dependencies) are at least started
      # Or, if direct dependency without relying on backend's health:
      # db:
      #   condition: service_healthy
      # redis:
      #   condition: service_healthy
    networks:
      - seculite_network
    restart: unless-stopped
    # Consider adding a healthcheck if Celery provides a way to check worker health.
    # For now, depends_on is the primary mechanism.
```

**Details:**
-   **`build`**: Identical to the `backend` service, as it requires the same Django application environment.
    -   `context: ./backend`
    -   `dockerfile: Dockerfile`
-   **`container_name: seculite_worker`**: Specific container name.
-   **`command: ["celery", "-A", "seculite_api", "worker", "-l", "info", "-Q", "default,scans", "-c", "2"]`**: This is the command to start a Celery worker.
    -   `celery`: The Celery command-line program.
    -   `-A seculite_api`: Specifies the Celery application instance (assuming your Celery app is discoverable via `seculite_api`, e.g., in `seculite_api/celery.py`).
    -   `worker`: Specifies that this should run as a worker.
    -   `-l info`: Sets the log level to info.
    -   `-Q default,scans`: Specifies the queues this worker will consume from. `default` is standard, and `scans` could be a dedicated queue for scan tasks.
    -   `-c 2`: Sets the concurrency level (number of child worker processes) to 2. Adjust based on expected load and server resources.
-   **`volumes`**:
    -   `./backend:/app`: Mounts the backend code, which is useful in development if you update task definitions and want the worker to pick them up without a rebuild (Celery worker might need a restart for some changes).
    -   `backend_media_data:/app/media`: If tasks need to read/write to media files (e.g., raw scan outputs), this volume provides access.
-   **`env_file: - .env`**: Loads the same environment variables as the backend, which will include Celery broker URL, backend settings, database URL, etc.
-   **`depends_on`**:
    -   `backend: condition: service_started`: This worker typically depends on the `backend` service being started because the Celery app instance is part of the Django project. `service_started` is a less strict condition than `service_healthy`. If the Django app needs to be fully healthy and responsive before workers start (e.g., if workers make API calls to the backend on startup, or if some Django app setup is critical), you might want a healthcheck on the backend service and use `condition: service_healthy`.
    -   Alternatively, you could define direct dependencies on `db` and `redis` with `service_healthy` conditions if the worker primarily needs them and less so the backend HTTP service itself being fully up.
-   **`networks: - seculite_network`**: Connects to the shared network.
-   **`restart: unless-stopped`**: Automatic restart policy.

### 3.5. `beat` (Celery Beat) Service
The `beat` service is responsible for scheduling periodic tasks. It also uses the same Docker image as the `backend` but runs the Celery beat command.

```yaml
services:
  # ... (db, redis, backend, worker services defined above)
  beat:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: seculite_beat
    # Command to start Celery beat. Uses DatabaseScheduler to store schedule in Django DB.
    # Make sure django-celery-beat is in requirements.txt and INSTALLED_APPS.
    command: >
      sh -c "rm -f /tmp/celerybeat.pid && \
             celery -A seculite_api beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler"
    volumes:
      - ./backend:/app # Mount backend code for development (live reload of task definitions)
    env_file:
      - .env
    depends_on:
      backend: # Depends on backend (and thus db and redis) to be started
        condition: service_started
      # Or, if direct dependency without relying on backend's health:
      # db:
      #   condition: service_healthy
      # redis:
      #   condition: service_healthy
    networks:
      - seculite_network
    restart: unless-stopped
```

**Details:**
-   **`build`**: Identical to the `backend` and `worker` services.
    -   `context: ./backend`
    -   `dockerfile: Dockerfile`
-   **`container_name: seculite_beat`**: Specific container name.
-   **`command: sh -c "rm -f /tmp/celerybeat.pid && celery -A seculite_api beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler"`**: This is the command to start Celery Beat.
    -   `sh -c "..."`: Runs the command within a shell.
    -   `rm -f /tmp/celerybeat.pid`: Removes any stale PID file that might prevent Celery Beat from starting. This is a common precaution.
    -   `celery -A seculite_api beat`: Starts the Celery Beat scheduler for the `seculite_api` application.
    -   `-l info`: Sets the log level to info.
    -   `--scheduler django_celery_beat.schedulers:DatabaseScheduler`: Configures Celery Beat to use the Django database as the storage for its schedule. This allows managing periodic tasks directly from the Django admin interface. Requires `django-celery-beat` to be installed and configured in your Django project (`INSTALLED_APPS`).
-   **`volumes`**:
    -   `./backend:/app`: Mounts the backend code. In development, if you change periodic task definitions in your code, Celery Beat might pick them up (though a restart is often safer for Beat).
-   **`env_file: - .env`**: Loads the same environment variables as the backend and worker, including database connection details (needed for `DatabaseScheduler`) and Celery settings.
-   **`depends_on`**:
    -   `backend: condition: service_started`: Similar to the `worker`, `beat` depends on the `backend` service (and implicitly its dependencies like `db` and `redis`) being available, especially since `DatabaseScheduler` needs the database.
-   **`networks: - seculite_network`**: Connects to the shared network.
-   **`restart: unless-stopped`**: Automatic restart policy. It's crucial for Beat to be running reliably to ensure scheduled tasks are dispatched.

### 3.6. `frontend` (Vue.js Build Stage - in Dockerfile)

The frontend (Vue.js application) is not defined as a separate long-running service in the `docker-compose.yml` file in the same way as the backend services. Instead, it follows a build-time process:

1.  **Dockerfile for Frontend**: A dedicated `frontend/Dockerfile` (detailed in Section 6) will be responsible for:
    *   Using a Node.js base image.
    *   Copying the Vue.js source code.
    *   Installing npm dependencies (`npm install` or `yarn install`).
    *   Building the Vue.js application into static assets (`npm run build` or `yarn build`). These assets typically consist of HTML, CSS, and JavaScript files.

2.  **Serving Static Assets**: The static assets generated by the frontend build process are then served by the `nginx` service (defined in Section 3.7).
    *   In a multi-stage `frontend/Dockerfile`, the build artifacts can be copied to a lightweight Nginx image stage.
    *   Alternatively, the `nginx` service in `docker-compose.yml` can mount a volume containing these pre-built assets, or copy them from a builder stage of the frontend Dockerfile.

This approach is standard for single-page applications (SPAs) like Vue.js, where the application is compiled into static files that a web server can serve directly. The `nginx` service will handle routing API requests to the `backend` service and serving the frontend application to users.

### 3.7. `nginx` (Web Server/Reverse Proxy) Service
The `nginx` service acts as the public-facing web server. It serves the static frontend assets and proxies dynamic API requests to the `backend` (Django/Gunicorn) service. It can also handle SSL termination and other web server responsibilities.

```yaml
services:
  # ... (db, redis, backend, worker, beat services defined above)
  nginx:
    image: nginx:1.25-alpine # Using a specific version of Nginx on Alpine
    container_name: seculite_nginx
    ports:
      - "80:80"      # HTTP port
      - "443:443"    # HTTPS port (if SSL is configured)
    volumes:
      # Mounts the Nginx configuration file (detailed in Section 7)
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      # Mounts the built frontend static assets.
      # This volume should be populated by the frontend build process.
      # Option 1: If frontend Dockerfile outputs to a local directory (e.g., ./frontend/dist)
      - ./frontend/dist:/var/www/frontend:ro
      # Option 2: If using a named volume populated by another service/stage (more advanced)
      # - frontend_static_assets:/var/www/frontend:ro
      # Mounts the collected static files from Django (for admin, etc., if served by Nginx)
      - backend_static_collected:/var/www/django_static:ro
      # Mounts media files if Nginx is to serve them directly (optional)
      # - backend_media_data:/var/www/media:ro
      # For SSL certificates (if handling SSL termination)
      # - ./nginx/certs:/etc/nginx/certs:ro
    depends_on:
      backend: # Nginx needs the backend to be up to proxy requests
        condition: service_started # Or service_healthy if backend has a reliable healthcheck for Gunicorn
      # No explicit dependency on frontend build here, assumes assets are available at startup.
    networks:
      - seculite_network
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "nginx", "-t"] # Test Nginx configuration
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 5s
```

**Details:**
-   **`image: nginx:1.25-alpine`**: Uses a specific, lightweight version of the official Nginx image.
-   **`container_name: seculite_nginx`**: Specific container name.
-   **`ports`**: Exposes standard HTTP (80) and HTTPS (443) ports to the host machine. HTTPS requires SSL certificate setup.
    -   `"80:80"`
    -   `"443:443"`
-   **`volumes`**:
    -   `./nginx/nginx.conf:/etc/nginx/nginx.conf:ro`: Mounts the custom Nginx configuration file (defined in Section 7) into the container in read-only mode (`:ro`).
    -   `./frontend/dist:/var/www/frontend:ro`: Mounts the directory containing the built static assets from the Vue.js frontend (assuming the build output is in `./frontend/dist`). Nginx will serve files from `/var/www/frontend`.
    -   `backend_static_collected:/var/www/django_static:ro`: Mounts the named volume where Django's `collectstatic` command places static files (e.g., for the Django admin interface). Nginx can be configured to serve these.
    -   *(Optional)* `backend_media_data:/var/www/media:ro`: If Nginx is configured to serve user-uploaded media files directly, this volume would be mounted.
    -   *(Optional)* `./nginx/certs:/etc/nginx/certs:ro`: For SSL certificates if Nginx handles HTTPS termination.
-   **`depends_on`**:
    -   `backend: condition: service_started`: Ensures that the `backend` service is started before Nginx, as Nginx will proxy requests to it. `service_healthy` could be used if the backend has a robust healthcheck.
-   **`networks: - seculite_network`**: Connects to the shared network.
-   **`restart: unless-stopped`**: Automatic restart policy.
-   **`healthcheck`**:
    -   `test: ["CMD", "nginx", "-t"]`: Uses `nginx -t` to test the validity of the Nginx configuration. This helps ensure Nginx doesn't start with a broken config.

Note on Frontend Assets: The `nginx` service relies on the frontend static assets being available in the specified volume (`./frontend/dist` or a named volume). The workflow usually involves building the frontend first (e.g., `docker-compose run --rm frontend npm run build`, if `frontend` was a temporary service to build, or via a multi-stage Dockerfile for `nginx` itself that includes the frontend build).

### 3.8. Volumes
Named volumes are used to persist data generated by and used by Docker containers. They are managed by Docker and are a preferred way to handle persistent storage compared to bind-mounting host directories for everything (especially for database data).

Here are the named volumes used in this `docker-compose.yml` setup:

```yaml
volumes:
  postgres_data:        # For PostgreSQL database files
    driver: local
  redis_data:           # For Redis data (if persistence is enabled/needed)
    driver: local
  backend_static_collected: # For Django's collected static files (e.g., admin, DRF assets)
    driver: local
  backend_media_data:     # For user-uploaded media files handled by Django
    driver: local
  # frontend_static_assets: # Optional: if using a named volume for frontend assets built by a separate service/stage
  #   driver: local
```

**Details:**
-   **`postgres_data`**: Persists the data for the `db` (PostgreSQL) service, stored in `/var/lib/postgresql/data` inside its container.
-   **`redis_data`**: Persists data for the `redis` service (if its configuration requires it). Stored in `/data` inside its container.
-   **`backend_static_collected`**: Used by the `backend` service (where `collectstatic` outputs) and potentially read by the `nginx` service to serve Django's static files (like admin interface assets).
-   **`backend_media_data`**: Used by the `backend` service for storing user-uploaded files (Django's `MEDIA_ROOT`) and potentially read by `nginx` if it's configured to serve media files directly.
-   **`driver: local`**: Specifies the default local driver for managing these volumes on the Docker host. This is usually sufficient for single-host deployments.

These volume definitions are placed at the root level of the `docker-compose.yml` file.

### 3.9. Networks
A custom Docker network allows services to communicate with each other using their service names as hostnames. It also provides better isolation from other Docker containers or networks running on the same host.

For SecuLite v2, we will define a single custom bridge network named `seculite_network`.

```yaml
networks:
  seculite_network:
    driver: bridge
    # For more advanced scenarios, you might specify IPAM (IP Address Management) options,
    # but for most local development and single-server setups, the default bridge driver
    # without extra options is sufficient.
    # Example IPAM config (usually not needed for simple setups):
    # ipam:
    #   driver: default
    #   config:
    #     - subnet: "172.28.0.0/16"
```

**Details:**
-   **`seculite_network`**: This is the name of our custom network. All services (`db`, `redis`, `backend`, `worker`, `beat`, `nginx`) will be attached to this network.
-   **`driver: bridge`**: Specifies that this network should use Docker's built-in `bridge` driver. This is the most common type for allowing inter-container communication on a single host.
    -   Containers on the same bridge network can reach each other by their service name (e.g., the `backend` service can connect to `db:5432`).
    -   Docker provides DNS resolution for service names within this network.

This `networks` definition is also placed at the root level of the `docker-compose.yml` file, similar to the `volumes` section.

With this, the definition of all services, volumes, and networks for the `docker-compose.yml` file is complete.

---

## 4. `backend/Dockerfile` Details

This Dockerfile is responsible for creating the image for the Django backend, Celery worker, and Celery beat services. It sets up the Python environment, installs dependencies, and copies the application code.

```dockerfile
# Stage 1: Base Python image and core dependencies
FROM python:3.11-slim-bullseye AS base

# Set environment variables to ensure Python output is sent straight to terminal
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set the working directory in the container
WORKDIR /app

# Install system dependencies required for Python packages (e.g., psycopg2, Pillow)
# Keep this minimal; add more as identified by package installation failures.
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    # For Pillow (if image processing is needed)
    # libjpeg-dev zlib1g-dev libtiff-dev libfreetype6-dev liblcms2-dev libwebp-dev \
    # For other common Python packages
    # libffi-dev libssl-dev \
    && apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install Poetry (Python package manager)
# Using a specific version for reproducibility
ARG POETRY_VERSION=1.7.1
RUN pip install "poetry==${POETRY_VERSION}"

# Copy only the files necessary for installing dependencies with Poetry
COPY ./backend/poetry.lock ./backend/pyproject.toml /app/

# Install project dependencies using Poetry
# --no-root: Do not install the project itself as editable, only its dependencies
# --no-dev: Do not install development dependencies (for a leaner production image)
RUN poetry install --no-root --no-dev

# Stage 2: Application code and runtime setup (can be same as base or a new stage)
# For simplicity here, we continue from the base stage.
# FROM base AS runtime

# Copy the rest of the backend application code into the working directory
COPY ./backend /app/

# Create a non-root user for running the application for better security
# ARG APP_USER=appuser
# RUN useradd -ms /bin/bash ${APP_USER}
# RUN chown -R ${APP_USER}:${APP_USER} /app
# USER ${APP_USER}
# Note: If using a non-root user, ensure entrypoint.sh and Gunicorn/Celery can run as this user,
# and that file permissions (especially for media/static volumes) are handled correctly.
# For simplicity in this initial plan, we will run as root, but a non-root user is recommended for production.

# Expose the port Gunicorn will run on (same as in docker-compose.yml)
EXPOSE 8000

# The entrypoint script will handle migrations and then execute the CMD
# CMD is defined in the docker-compose.yml for each service (backend, worker, beat)
ENTRYPOINT ["/app/entrypoint.sh"]
```

**Key Steps and Explanations:**

1.  **`FROM python:3.11-slim-bullseye AS base`**:
    *   Starts from an official Python 3.11 slim image based on Debian Bullseye. Slim images are smaller than the full Debian images.
    *   `AS base`: Names this stage `base`, allowing it to be referenced later if using multi-stage builds (though not heavily utilized here for simplicity yet).

2.  **`ENV PYTHONDONTWRITEBYTECODE 1` and `ENV PYTHONUNBUFFERED 1`**:
    *   `PYTHONDONTWRITEBYTECODE`: Prevents Python from writing `.pyc` files to disc (useful in containers).
    *   `PYTHONUNBUFFERED`: Ensures that Python output (e.g., print statements, logs) is sent directly to the terminal without being buffered, which is important for Docker logging.

3.  **`WORKDIR /app`**:
    *   Sets the default working directory for subsequent `RUN`, `CMD`, `ENTRYPOINT`, `COPY`, and `ADD` instructions.

4.  **`RUN apt-get update && apt-get install -y ...`**:
    *   Installs necessary system-level dependencies. `build-essential` and `libpq-dev` are common for Django projects using PostgreSQL (for compiling `psycopg2`).
    *   Includes commented-out examples for other common libraries like those needed for Pillow or `libffi`.
    *   `--no-install-recommends` reduces unnecessary packages.
    *   `apt-get clean && rm -rf /var/lib/apt/lists/*` cleans up apt cache to keep the image size down.

5.  **`ARG POETRY_VERSION=1.7.1` and `RUN pip install "poetry==${POETRY_VERSION}"`**:
    *   Installs Poetry, a dependency management tool for Python. Using a specific version ensures reproducibility.

6.  **`COPY ./backend/poetry.lock ./backend/pyproject.toml /app/`**:
    *   Copies only the `poetry.lock` and `pyproject.toml` files first. This leverages Docker's layer caching. If these files haven't changed, Docker can reuse the cached layer from the next step (dependency installation), speeding up builds when only application code changes.

7.  **`RUN poetry install --no-root --no-dev`**:
    *   Installs Python dependencies defined in `pyproject.toml` using the versions specified in `poetry.lock`.
    *   `--no-root`: Skips installing the project package itself in editable mode.
    *   `--no-dev`: Excludes development dependencies (like testing tools) to keep the production image lean. For a development-specific stage, you might omit `--no-dev`.

8.  **`COPY ./backend /app/`**:
    *   Copies the entire `./backend` directory (containing your Django project) into the `/app` directory in the image.

9.  **Non-Root User (Commented Out for Initial Simplicity)**:
    *   The commented-out section shows how to create and switch to a non-root user (`appuser`). This is a security best practice for production.
    *   *Decision*: For the initial setup, we'll proceed with the root user to simplify volume permissions and Gunicorn/Celery execution, but this should be revisited and implemented before any production deployment.

10. **`EXPOSE 8000`**:
    *   Documents that the container will listen on port 8000 at runtime. This doesn't actually publish the port; publishing is done in `docker-compose.yml`.

11. **`ENTRYPOINT ["/app/entrypoint.sh"]`**:
    *   Specifies the `entrypoint.sh` script (detailed in Section 5) as the command to be executed when the container starts.
    *   The actual command to run the application (Gunicorn, Celery worker, Celery beat) will be passed as an argument to this entrypoint script from the `command` directive in the `docker-compose.yml` file for each respective service.

This Dockerfile provides a solid foundation for building the backend application image. It prioritizes caching, dependency management with Poetry, and includes placeholders for security best practices like using a non-root user.

---

## 5. `backend/entrypoint.sh` Details

The `entrypoint.sh` script is executed when any container using the `backend` image starts (i.e., `backend`, `worker`, `beat` services). Its primary purpose is to handle setup tasks like waiting for the database to be ready, applying Django database migrations, and then executing the main command passed to the container (e.g., Gunicorn, Celery worker/beat).

This script should be placed in the `backend/` directory and made executable (`chmod +x backend/entrypoint.sh`).

```bash
#!/bin/sh

# Exit immediately if a command exits with a non-zero status.
set -e

# Function to check if PostgreSQL is ready
wait_for_postgres() {
  echo "Waiting for PostgreSQL to be ready..."
  # The PGPASSWORD environment variable should be set for the psql command to work without a password prompt.
  # It's typically set in the .env file and loaded by docker-compose.
  until psql -h "${DB_HOST:-db}" -U "${DB_USER:-postgres}" -d "${DB_NAME:-postgres}" -c '\q' 2>/dev/null; do
    echo "PostgreSQL is unavailable - sleeping"
    sleep 1
  done
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

```

**Key Features and Explanations:**

1.  **`#!/bin/sh`**: Shebang indicating the script should be run with `sh` (Bourne shell).
2.  **`set -e`**: Exits the script immediately if any command fails. This is good for catching errors early.
3.  **`wait_for_postgres()` Function**:
    *   This function polls the PostgreSQL database to check if it's ready to accept connections before proceeding.
    *   It uses `psql -h "${DB_HOST:-db}" ... -c '\q'`. The environment variables `DB_HOST`, `DB_USER`, `DB_NAME` (and implicitly `PGPASSWORD`) should be available from the `.env` file.
    *   The `:-db` syntax provides a default value if the variable is unset or null.
4.  **Command Handling (`case "$1" in ... esac`)**:
    *   The script inspects the first argument (`$1`) passed to it. This argument is typically the first part of the `command` specified in `docker-compose.yml`.
    *   **`"gunicorn"`)**: If the command is for Gunicorn (our `backend` service):
        *   It optionally waits for the database using `wait_for_postgres` (controlled by `WAIT_FOR_DB` env var, defaulting to true).
        *   Runs Django database migrations: `poetry run python manage.py migrate --noinput`.
        *   Collects static files: `poetry run python manage.py collectstatic --noinput --clear`.
        *   Commented out `chown` commands are placeholders for when a non-root user is implemented, to ensure correct file permissions for volumes.
    *   **`"celery_worker"` and `"celery_beat"`)**: If the command is for Celery worker or beat:
        *   It optionally waits for the database (controlled by `WAIT_FOR_DB_CELERY` or `WAIT_FOR_DB_CELERY_BEAT` env vars).
        *   `shift`: This command removes the first argument (e.g., `celery_worker`) from the list of positional parameters (`$@`). This is because the actual Celery command (e.g., `celery -A seculite_api worker ...`) follows this marker. The `exec "$@"` at the end will then run the intended Celery command.
    *   **`*)` (Default case)**: If the first argument doesn't match known services, it simply proceeds to execute the command as is. This allows running other Django management commands or a shell, e.g., `docker-compose run backend poetry run python manage.py createsuperuser`.
5.  **`exec "$@"`**:
    *   This is the crucial final step. It replaces the current shell process with the command specified by `"$@"` (all arguments passed to the script, potentially modified by `shift`).
    *   Using `exec` ensures that the main application (Gunicorn, Celery, etc.) becomes PID 1 in the container (or at least the direct child of the entrypoint that receives signals properly), which is important for signal handling (like `SIGTERM` for graceful shutdown).

**How it integrates with `docker-compose.yml`:**

-   The `ENTRYPOINT ["/app/entrypoint.sh"]` in `backend/Dockerfile` sets this script to run first.
-   The `command:` directive in `docker-compose.yml` for services using this image will provide the arguments to this script.
    -   For `backend` service: `command: ["gunicorn", "seculite_api.wsgi:application", ...]`
        *   `$1` in entrypoint.sh will be `gunicorn`.
    -   For `worker` service: `command: ["celery_worker", "celery", "-A", "seculite_api", "worker", ...]`
        *   `$1` will be `celery_worker`. After `shift`, `"$@"` becomes `celery -A seculite_api worker ...`.
    -   For `beat` service: `command: ["celery_beat", "celery", "-A", "seculite_api", "beat", ...]`
        *   `$1` will be `celery_beat`. After `shift`, `"$@"` becomes `celery -A seculite_api beat ...`.

This entrypoint script provides flexibility and handles common startup routines for a Django application in Docker.

---

## 6. `frontend/Dockerfile` Details (Multi-stage)

This Dockerfile is responsible for building the Vue.js frontend application into static assets. It uses a multi-stage build to ensure the final image that Nginx might use (or the assets it serves) are as small as possible, without including the Node.js build environment.

The static assets will be served by the `nginx` service, either by copying them into an Nginx image or by Nginx mounting a volume where these assets are placed.

```dockerfile
# Stage 1: Build the Vue.js application
# Use an official Node.js LTS (Long Term Support) image as the base for building.
# Alpine versions are smaller. Choose one that matches your project's Node.js version needs.
FROM node:18-alpine AS builder

# Set the working directory in the container for the frontend app
WORKDIR /app/frontend

# Copy package.json and lock files, then run `npm ci` (or yarn equivalent).
COPY ./frontend/package.json ./frontend/package-lock.json* ./frontend/yarn.lock* ./
# The `*` is to handle cases where lock files might not exist initially or one is preferred.

# Install dependencies based on the lock file
# If using npm:
RUN npm ci
# If using yarn:
# RUN yarn install --frozen-lockfile

# Copy the rest of the frontend application code
COPY ./frontend .

# Build the Vue.js application for production
# This command might vary based on your Vue project setup (e.g., Vue CLI, Vite)
RUN npm run build
# If using yarn:
# RUN yarn build

# At this point, the /app/frontend/dist directory (or similar, e.g., /app/frontend/build)
# contains the compiled static assets of the Vue.js application.

# Stage 2: (Optional) Serve with Nginx directly from a leaner image
# This stage is useful if you want this Dockerfile to produce a self-contained Nginx image
# serving the frontend. Alternatively, the nginx service in docker-compose.yml can
# directly mount or copy assets from the 'builder' stage if configured appropriately.

# FROM nginx:1.25-alpine

# Copy the built static assets from the 'builder' stage
# COPY --from=builder /app/frontend/dist /usr/share/nginx/html

# Copy a custom Nginx configuration file (if needed for this specific frontend serving setup)
# COPY ./nginx/nginx-frontend-specific.conf /etc/nginx/conf.d/default.conf

# Expose port 80 for Nginx
# EXPOSE 80

# Default command to start Nginx
# CMD ["nginx", "-g", "daemon off;"]

# For SecuLite v2, we will primarily rely on the main `nginx` service defined in
# `docker-compose.yml` (Section 3.7) to serve these assets. That Nginx service will
# typically copy assets from the `builder` stage of this Dockerfile or mount a volume
# that is populated by running the build stage of this Dockerfile.
# The key output of this Dockerfile is the `/app/frontend/dist` directory in the `builder` stage.
```

**Key Steps and Explanations:**

1.  **`FROM node:18-alpine AS builder` (Builder Stage)**:
    *   Starts with an official Node.js image (e.g., version 18 LTS, Alpine variant for smaller size) named `builder`.
    *   This stage will contain all the tools and dependencies needed to build the Vue.js application.

2.  **`WORKDIR /app/frontend`**:
    *   Sets the working directory for the frontend build process.

3.  **`COPY ./frontend/package.json ./frontend/package-lock.json* ./frontend/yarn.lock* ./`**:
    *   Copies the package definition and lock files first to leverage Docker's build cache. If these haven't changed, subsequent `npm ci` or `yarn install` steps can be skipped if cached.

4.  **`RUN npm ci` (or `RUN yarn install --frozen-lockfile`)**:
    *   Installs project dependencies using `npm ci` (which is generally preferred for CI/build environments as it uses the `package-lock.json` strictly) or `yarn install` with `--frozen-lockfile`.

5.  **`COPY ./frontend .`**:
    *   Copies the rest of the Vue.js application source code into the working directory.

6.  **`RUN npm run build` (or `RUN yarn build`)**:
    *   Executes the build script defined in `package.json` (e.g., `vue-cli-service build`, `vite build`). This compiles the Vue.js application into static HTML, CSS, and JavaScript files, typically outputting them to a `dist` or `build` directory (e.g., `/app/frontend/dist`).

7.  **Stage 2 (Optional Nginx Stage - Commented Out)**:
    *   The commented-out section shows an example of a second stage that could take the build artifacts from the `builder` stage and serve them using a lean Nginx image.
    *   `COPY --from=builder /app/frontend/dist /usr/share/nginx/html`: This command is crucial in multi-stage builds. It copies files from a previous stage (`builder`) into the current stage.
    *   **Primary Approach for SecuLite v2**: As noted, our main `nginx` service (Section 3.7) will be responsible for serving these assets. It can achieve this by:
        *   Using `COPY --from=...` if the `nginx` service itself is built using a Dockerfile that incorporates the Vue build stage.
        *   More commonly, by mounting a host directory (e.g., `./frontend/dist`) that is populated by running the build: `docker-compose run --rm frontend_builder` (where `frontend_builder` would be a temporary service definition in `docker-compose.yml` just for running the build from this Dockerfile and outputting to a shared volume or host directory).
        *   Or, if the Nginx service in `docker-compose.yml` has a `build` context, its Dockerfile can directly reference the `builder` stage of this `frontend/Dockerfile` to copy the assets.

**Integration with `docker-compose.yml` and `nginx` service:**

The primary role of this `frontend/Dockerfile` is to produce the static build artifacts. The `nginx` service defined in `docker-compose.yml` (Section 3.7) will then take these artifacts and serve them. A common pattern is:

1.  Define a simple service in `docker-compose.yml` that just builds the frontend (if not part of the main `nginx` image build):
    ```yaml
    # In docker-compose.yml (example snippet for building assets)
    services:
      frontend_builder: # Temporary service just for building
        build:
          context: ./frontend
          dockerfile: Dockerfile
          target: builder # Only build up to the 'builder' stage
        volumes:
          - ./frontend/dist:/app/frontend/dist # Output build to host directory
    ```
    Then you would run `docker-compose run --rm frontend_builder` (assuming you name the service `frontend_builder`) before starting the main stack. The `nginx` service would then mount `./frontend/dist`.

2.  Alternatively, the `nginx` service's Dockerfile can incorporate these stages directly or copy from the `builder` stage. If `nginx` service in `docker-compose.yml` has its own `Dockerfile` (e.g. `nginx/Dockerfile`), that file could look like:
    ```dockerfile
    # In nginx/Dockerfile (example)
    # Stage 1: Build frontend (copied from frontend/Dockerfile)
    FROM node:18-alpine AS builder
    WORKDIR /app/frontend
    COPY ./frontend/package.json ./frontend/package-lock.json* ./frontend/yarn.lock* ./
    RUN npm ci
    COPY ./frontend .
    RUN npm run build

    # Stage 2: Actual Nginx image
    FROM nginx:1.25-alpine
    COPY --from=builder /app/frontend/dist /usr/share/nginx/html
    COPY ./nginx/nginx.conf /etc/nginx/nginx.conf
    ```
    In this case, the `nginx` service in `docker-compose.yml` would have `build: ./nginx`.

For this plan, we assume the `nginx` service (Section 3.7) will mount a host directory like `./frontend/dist` which is populated by running the build defined in `frontend/Dockerfile`. The command to populate `./frontend/dist` might be `docker compose run --rm frontend_build_service` if we define a service named `frontend_build_service` that uses `frontend/Dockerfile` and whose `npm run build` output directory (`/app/frontend/dist`) is volume-mounted to `./frontend/dist` on the host.

---

## 7. `nginx/nginx.conf` Details (Example for `nginx` service)

This Nginx configuration file (`nginx/nginx.conf`) will be mounted into the `nginx` service container. It defines how Nginx handles incoming HTTP/HTTPS requests, serves static frontend assets, and proxies API requests to the Django backend.

This example includes common settings for serving a SPA (Single Page Application) like Vue.js and a Django backend, along with placeholders for SSL and security headers.

```nginx
# Basic Nginx worker and event settings
user nginx;
worker_processes auto; # Can be set to the number of CPU cores
pid /var/run/nginx.pid;

events {
    worker_connections 1024; # Max connections per worker
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    # Logging format
    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                      '$status $body_bytes_sent "$http_referer" '
                      '"$http_user_agent" "$http_x_forwarded_for"';

    access_log /var/log/nginx/access.log main;
    error_log /var/log/nginx/error.log warn;

    # Enable Gzip compression
    gzip on;
    gzip_vary on;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types text/plain text/css application/json application/javascript application/x-javascript text/xml application/xml application/xml+rss text/javascript image/svg+xml;

    # Define an upstream for the Django backend application
    # 'backend' is the service name defined in docker-compose.yml
    # Port 8000 is where Gunicorn is listening inside the backend container
    upstream django_backend {
        server backend:8000;
    }

    server {
        listen 80 default_server;
        # listen 443 ssl http2 default_server; # Uncomment for HTTPS
        # server_name yourdomain.com www.yourdomain.com; # Replace with your domain

        # SSL Configuration (Uncomment and configure if using HTTPS)
        # ssl_certificate /etc/nginx/certs/yourdomain.com.crt;
        # ssl_certificate_key /etc/nginx/certs/yourdomain.com.key;
        # ssl_protocols TLSv1.2 TLSv1.3;
        # ssl_prefer_server_ciphers on;
        # ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384';
        # ssl_session_cache shared:SSL:10m;
        # ssl_session_timeout 1d;
        # ssl_stapling on;
        # ssl_stapling_verify on;
        # add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;

        # Path for Django static files (e.g., /static/admin/)
        # Assumes backend_static_collected volume is mounted at /var/www/django_static in nginx service
        location /static/ {
            alias /var/www/django_static/;
            expires 7d; # Cache static files for 7 days
            access_log off; # Disable access logging for static files
        }

        # Path for Django media files (e.g., user-uploaded content)
        # Assumes backend_media_data volume is mounted at /var/www/media in nginx service
        location /media/ {
            alias /var/www/media/;
            expires 7d; # Cache media files for 7 days
            access_log off;
        }

        # Location for API requests to be proxied to the Django backend
        location /api/ {
            proxy_pass http://django_backend; # Forward to the upstream defined above
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_set_header Host $http_host;
            proxy_redirect off;
            proxy_buffering off; # Useful for streaming responses or Server-Sent Events
            # Add other proxy headers if needed by your application
        }

        # Location for serving the frontend static assets (Vue.js app)
        # Assumes frontend static assets are in /var/www/frontend
        location / {
            root /var/www/frontend;
            try_files $uri $uri/ /index.html; # For SPA routing: try file, then directory, then fallback to index.html
            expires -1; # Do not cache index.html to ensure users get the latest app version

            # Security headers
            # add_header X-Frame-Options "SAMEORIGIN" always;
            # add_header X-Content-Type-Options "nosniff" always;
            # add_header X-XSS-Protection "1; mode=block" always;
            # add_header Referrer-Policy "strict-origin-when-cross-origin" always;
            # add_header Content-Security-Policy "default-src 'self'; ..." always; # Define your CSP
        }

        # Optional: Add specific error pages or other configurations
        # error_page 500 502 503 504 /50x.html;
        # location = /50x.html {
        #     root /usr/share/nginx/html; # Default Nginx error page location
        # }
    }
}
```

**Key Components and Explanations:**

1.  **Basic Settings (`user`, `worker_processes`, `pid`, `events`)**: Standard Nginx global settings.
2.  **`http` Block**: Defines settings for HTTP traffic.
    *   `include /etc/nginx/mime.types; default_type application/octet-stream;`: Basic MIME type handling.
    *   `log_format`, `access_log`, `error_log`: Configure logging.
    *   `gzip ...`: Enables and configures Gzip compression for better performance.
3.  **`upstream django_backend`**: Defines a group of servers for the Django backend.
    *   `server backend:8000;`: `backend` is the service name from `docker-compose.yml`, and `8000` is the port Gunicorn listens on within that service's container. Nginx will load balance requests if multiple servers were listed (not applicable here).
4.  **`server` Block**: Configures a virtual server.
    *   `listen 80 default_server;`: Listens on port 80 for HTTP requests. `default_server` makes this the default for requests not matching any other `server_name`.
    *   `# listen 443 ssl http2 default_server;`: Commented out HTTPS listener. Requires SSL certificates.
    *   `# server_name yourdomain.com www.yourdomain.com;`: Should be your actual domain(s).
    *   **SSL Configuration (Commented Out)**: Placeholders for `ssl_certificate`, `ssl_certificate_key`, protocols, ciphers, and HSTS header. These are crucial for production HTTPS.
5.  **`location /static/`**: Serves Django's collected static files (e.g., admin interface assets).
    *   `alias /var/www/django_static/;`: Maps requests for `/static/...` to files in `/var/www/django_static/` inside the Nginx container. This path corresponds to the `backend_static_collected` volume mount.
    *   `expires 7d; access_log off;`: Caching and logging settings.
6.  **`location /media/`**: Serves Django's user-uploaded media files.
    *   `alias /var/www/media/;`: Maps requests for `/media/...` to files in `/var/www/media/`. This path corresponds to the `backend_media_data` volume mount.
7.  **`location /api/`**: Proxies requests starting with `/api/` to the Django backend.
    *   `proxy_pass http://django_backend;`: Forwards the request to the `django_backend` upstream group.
    *   `proxy_set_header ...`: Sets important headers for the backend to understand the original request (e.g., client IP, protocol, host).
    *   `proxy_redirect off; proxy_buffering off;`: Common proxy settings.
8.  **`location /`**: Serves the Vue.js Single Page Application (SPA).
    *   `root /var/www/frontend;`: Sets the root directory for these requests to `/var/www/frontend`, where the Vue.js app's static assets (from `./frontend/dist`) are mounted.
    *   `try_files $uri $uri/ /index.html;`: This is key for SPAs. Nginx first tries to find a file matching the URI (`$uri`), then a directory (`$uri/`). If neither exists (e.g., for a client-side route like `/dashboard`), it serves `/index.html`. The Vue.js router then handles the client-side navigation.
    *   `expires -1;`: Prevents caching of `index.html` to ensure users get the latest version of the SPA.
    *   **Security Headers (Commented Out)**: Examples of important security headers like `X-Frame-Options`, `X-Content-Type-Options`, `X-XSS-Protection`, `Referrer-Policy`, and `Content-Security-Policy`. These should be configured carefully.

This `nginx.conf` provides a robust starting point. It should be placed in an `nginx` directory at the project root (e.g., `./nginx/nginx.conf`) and mounted into the Nginx container as specified in the `nginx` service definition in `docker-compose.yml` (Section 3.7).

---

## 8. Environment Variables (`.env.example`)

An `.env.example` file should be created at the root of the project to provide a template for the actual `.env` file that developers will use. The `.env` file itself should be added to `.gitignore` to prevent committing sensitive credentials.

This file will list all necessary environment variables for the different services.

```env
# .env.example - Environment variables for SecuLite v2
# Copy this file to .env and fill in your actual values.
# DO NOT COMMIT .env TO VERSION CONTROL.

# General Settings
# ----------------
# Set to "development" or "production"
# In Django, this might influence DEBUG settings, allowed hosts, etc.
ENVIRONMENT=development

# Django Backend Settings
# -----------------------
# SECURITY WARNING: keep the secret key used in production secret!
# Generate a new secret key for your project, e.g., using python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
DJANGO_SECRET_KEY=your_django_secret_key_here

# Set to True for development, False for production
DJANGO_DEBUG=True

# Allowed hosts for Django. For development, localhost and 127.0.0.1 are common.
# For production, set to your actual domain(s), e.g., "yourdomain.com,www.yourdomain.com"
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,backend

# Internal port the Django app (Gunicorn) runs on inside the container
DJANGO_INTERNAL_PORT=8000

# PostgreSQL Database Settings (for Django and Celery Beat Scheduler)
# -------------------------------------------------------------------
DB_ENGINE=django.db.backends.postgresql
DB_NAME=seculite_db
DB_USER=seculite_user
DB_PASSWORD=your_secure_password_for_db_user
DB_HOST=db # This is the service name of the PostgreSQL container in docker-compose.yml
DB_PORT=5432

# PGPASSWORD is used by psql in entrypoint.sh if DB_PASSWORD is not directly used by psql
# Ensure this matches DB_PASSWORD if psql needs it explicitly.
PGPASSWORD=${DB_PASSWORD}

# Redis Settings (for Celery Broker and potentially Caching)
# ---------------------------------------------------------
REDIS_HOST=redis # Service name of the Redis container
REDIS_PORT=6379
REDIS_DB_CELERY=0 # Database number for Celery
REDIS_DB_CACHE=1  # Database number for Django caching (if used)

# Celery Settings
# ---------------
# Broker URL (using Redis)
CELERY_BROKER_URL=redis://${REDIS_HOST}:${REDIS_PORT}/${REDIS_DB_CELERY}
# Result Backend URL (can also be Redis or PostgreSQL)
# Using Redis for results:
CELERY_RESULT_BACKEND=redis://${REDIS_HOST}:${REDIS_PORT}/${REDIS_DB_CELERY}
# Or using Django DB for results (requires django-celery-results package):
# CELERY_RESULT_BACKEND=django-db

# Celery Beat Scheduler Settings (if using django-celery-beat)
# -----------------------------------------------------------
# The entrypoint.sh script for the 'beat' service uses django_celery_beat.schedulers:DatabaseScheduler
# which stores schedules in the Django database. No specific env vars needed here beyond DB access.

# Frontend Settings (if any need to be passed at build time or runtime via Nginx)
# -----------------------------------------------------------------------------------
# Example: API base URL for the frontend to connect to
# This is typically configured in the Vue.js app itself, but can be influenced by build-time env vars.
# VUE_APP_API_BASE_URL=/api

# Nginx Settings (related to domain names, SSL - though often managed in nginx.conf directly)
# ---------------------------------------------------------------------------------------------
# NGINX_HOST=localhost
# NGINX_PORT=80

# Entrypoint Script Variables (Optional control flags)
# ----------------------------------------------------
# Set to "false" to skip waiting for DB on Gunicorn startup (not recommended for first run)
WAIT_FOR_DB=true
# Set to "false" to skip waiting for DB on Celery worker startup
WAIT_FOR_DB_CELERY=true
# Set to "false" to skip waiting for DB on Celery beat startup
WAIT_FOR_DB_CELERY_BEAT=true

# Add any other application-specific settings here
# E.g., API keys for external services, email server settings, etc.

```

**Explanation of Key Variables:**

-   **`ENVIRONMENT`**: Indicates the runtime environment (e.g., `development`, `production`). Can be used by Django to adjust settings.
-   **`DJANGO_SECRET_KEY`**: A critical security setting for Django. Must be unique and kept secret in production.
-   **`DJANGO_DEBUG`**: Toggles Django's debug mode. Should be `False` in production.
-   **`DJANGO_ALLOWED_HOSTS`**: A list of host/domain names that the Django site can serve.
-   **Database Variables (`DB_*`, `PGPASSWORD`)**: Credentials and connection details for PostgreSQL. `DB_HOST` is set to `db`, the service name of the PostgreSQL container.
-   **Redis Variables (`REDIS_*`)**: Connection details for Redis. `REDIS_HOST` is set to `redis`, the service name.
-   **Celery Variables (`CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`)**: Configure Celery's message broker and result backend, pointing to the Redis service.
-   **Entrypoint Script Variables (`WAIT_FOR_DB*`)**: Boolean flags to control whether the entrypoint script waits for the database before proceeding for different services. Useful for certain startup scenarios or debugging.

This `.env.example` file should be comprehensive enough to get a developer started. They will copy it to `.env`, fill in secrets (like `DJANGO_SECRET_KEY` and `DB_PASSWORD`), and can adjust other settings as needed for their local environment.

---

## 9. Development Workflow Considerations

This section outlines common practices and commands for developers working with this Dockerized environment.

1.  **Initial Setup**:
    *   Ensure Docker and Docker Compose are installed.
    *   Copy `.env.example` to `.env` and fill in the required values (especially `DJANGO_SECRET_KEY`, `DB_USER`, `DB_PASSWORD`).
    *   Ensure the `backend/entrypoint.sh` script is executable: `chmod +x backend/entrypoint.sh`.

2.  **Building and Starting Services**:
    *   **First-time build or when Dockerfiles change**: `docker-compose build` (or `docker compose build` for newer syntax).
    *   **Build and start all services**: `docker-compose up --build` (or `docker compose up --build`). The `--build` flag ensures images are rebuilt if their Dockerfile or context has changed.
    *   **Start services (if already built)**: `docker-compose up` (or `docker compose up`).
    *   **Start in detached mode (run in background)**: `docker-compose up -d`.

3.  **Code Development and Live Reloading**:
    *   **Backend (Django)**: The `backend` service in `docker-compose.yml` mounts `./backend:/app`. When you save changes to Python files in your local `./backend` directory, Gunicorn (if configured for auto-reload, which is typical for development, or by restarting the container) or the Django development server (if used instead of Gunicorn during dev) should pick up these changes. For Gunicorn, a reload might be triggered by sending a SIGHUP signal to the Gunicorn master process or by restarting the `backend` container if live reload isn't automatic for Gunicorn.
        *   *Note on Gunicorn auto-reload*: Standard Gunicorn doesn't auto-reload code as effectively as `python manage.py runserver`. For development, some teams might temporarily switch the `backend` service's command to use `poetry run python manage.py runserver 0.0.0.0:8000` for better hot-reloading. This plan currently uses Gunicorn for consistency with production-like setup, so a container restart (`docker-compose restart backend`) might be needed for some backend changes to take effect if Gunicorn itself doesn't reload.
    *   **Frontend (Vue.js)**: The `frontend/Dockerfile` builds static assets. For live reloading during Vue.js development, you would typically run the Vue development server (e.g., `npm run serve` or `yarn serve`) directly on your host machine or within a dedicated development container that mounts the frontend source code and has port forwarding. The Nginx service in this Docker setup is primarily for serving the *built* production assets.
        *   To integrate Vue.js live reload with Docker, you might have a separate `docker-compose.dev.yml` that overrides the `frontend` part or adds a new service for the Vue dev server, e.g., mapping port 8080 from the Vue dev server container to the host.
        *   Alternatively, develop the frontend outside Docker using Node/npm on your host, pointing its API requests to `http://localhost/api/` (assuming Nginx is running via Docker and proxying to the backend).

4.  **Accessing Services**:
    *   **Frontend Application**: `http://localhost` (or `http://localhost:PORT` if Nginx port 80 is mapped to a different host port).
    *   **Backend API**: Via Nginx proxy at `http://localhost/api/`. Direct access to `http://localhost:8000` (Gunicorn) might also be possible if that port is mapped in `docker-compose.yml` for the `backend` service.
    *   **Database**: If port 5432 is mapped for the `db` service, you can connect using a PostgreSQL client to `localhost:5432` with credentials from `.env`.
    *   **Redis**: If port 6379 is mapped, tools like `redis-cli` can connect to `localhost:6379`.

5.  **Running Management Commands (Django)**:
    *   Use `docker-compose exec <service_name> <command>` or `docker-compose run --rm <service_name> <command>`.
    *   Example: Create a superuser: `docker-compose exec backend poetry run python manage.py createsuperuser`
    *   Example: Run specific tests: `docker-compose exec backend poetry run python manage.py test myapp.tests.SpecificTest`
    *   Example: Open a Django shell: `docker-compose exec backend poetry run python manage.py shell`
    *   `docker-compose run --rm ...` is useful for one-off commands as it starts a new container and removes it after execution.

6.  **Viewing Logs**:
    *   **All services (aggregated)**: `docker-compose logs` (or `docker compose logs`).
    *   **Follow logs (live tail)**: `docker-compose logs -f`.
    *   **Logs for a specific service**: `docker-compose logs -f backend`.

7.  **Stopping Services**:
    *   **Stop services (if running in foreground with `docker-compose up`)**: `Ctrl+C`.
    *   **Stop services (if running in detached mode or from another terminal)**: `docker-compose stop`.

8.  **Cleaning Up**:
    *   **Stop and remove containers**: `docker-compose down`.
    *   **Stop and remove containers, volumes, and images defined in compose file**: `docker-compose down --volumes --rmi local` (Use with caution, `--volumes` will delete data in named volumes like `postgres_data` unless they are declared as `external`).
    *   **Prune unused Docker objects (globally)**: `docker system prune -a --volumes` (Very destructive, removes all unused images, containers, networks, and volumes not associated with any running container).

9.  **Building Frontend Assets for Nginx**:
    *   As per Section 6, the `frontend/Dockerfile` defines how to build static assets.
    *   You might need a command to trigger this build and place assets where Nginx can find them (e.g., in `./frontend/dist` if Nginx mounts that).
    *   One way: Define a builder service in `docker-compose.yml` as shown in Section 6's "Integration" notes, then run: `docker-compose run --rm frontend_builder` (assuming you name the service `frontend_builder`).
    *   This step is manual before `docker-compose up` if Nginx relies on host-mounted pre-built assets. If Nginx builds the frontend as part of its own image, then `docker-compose build nginx` or `docker-compose up --build` handles it.

10. **Debugging**:
    *   **Python (Backend)**: Use `pdb` or `ipdb`. You can attach to a running container using `docker-compose exec backend <command_to_start_debugger_or_shell>` or modify the service command to start with a debugger attached.
        *   Example for `pdb` in `manage.py` or views: `import pdb; pdb.set_trace()`.
        *   Ensure service is run with `tty: true` and `stdin_open: true` in `docker-compose.yml` for interactive debugging.
    *   **Vue.js (Frontend)**: Use browser developer tools. If running the Vue dev server (see point 3), it provides HMR and good debugging support.

This workflow aims for a balance between a production-like setup and development ease.

---

## 10. Production Deployment Considerations (Brief)

While this Docker setup provides a good foundation, deploying to production requires additional considerations beyond the scope of local development. Here are some key points:

1.  **Environment Variables and Secrets Management**:
    *   **`ENVIRONMENT=production`**: Set this in your production `.env` file or server environment.
    *   **`DJANGO_DEBUG=False`**: Crucial for security and performance.
    *   **`DJANGO_SECRET_KEY`**: Must be a strong, unique key loaded securely (e.g., from environment variables, secrets management service like HashiCorp Vault, AWS Secrets Manager, etc.). **Do not hardcode or use the development key.**
    *   **Database Credentials (`DB_PASSWORD`, etc.)**: Manage these securely, not in version control. Use environment variables injected by the deployment platform or a secrets manager.
    *   **`.env` File**: The `.env` file should generally not be deployed to production servers directly. Instead, environment variables should be provided by the hosting platform or orchestration system.

2.  **Security Hardening**:
    *   **Non-Root Users**: Ensure all services (Django/Gunicorn, Celery, Nginx) run as non-root users inside their containers. This involves adding `USER` directives in Dockerfiles and ensuring file permissions are correct for volumes and application directories.
    *   **`DJANGO_ALLOWED_HOSTS`**: Configure this strictly to your production domain(s).
    *   **HTTPS Enforcement**: Configure Nginx to redirect all HTTP traffic to HTTPS. Implement SSL/TLS correctly with strong ciphers and protocols (see `nginx.conf` placeholders).
    *   **Security Headers**: Implement robust security headers in Nginx (`Strict-Transport-Security`, `Content-Security-Policy`, `X-Frame-Options`, `X-Content-Type-Options`, etc.).
    *   **Firewall**: Ensure appropriate firewall rules on the host server(s).
    *   **Regular Updates**: Keep base images (Python, Node, Nginx, OS) and all software packages updated to patch vulnerabilities.

3.  **Image Optimization and Builds**:
    *   **Leaner Images**: Minimize image sizes. Use multi-stage builds effectively. Remove build tools and development dependencies from final production images.
    *   **No Development Mounts**: In production, do not mount source code directories (`./backend:/app`, `./frontend:/app`) into containers. The application code should be baked into the image.

4.  **Serving Static and Media Files**:
    *   **`collectstatic`**: Ensure `python manage.py collectstatic` is run during the build process for the `backend` image, so all static files are part of the image or a dedicated volume.
    *   **Nginx Serving**: Nginx should serve all static files (Django admin, DRF, frontend app) and user-uploaded media files.
    *   **Content Delivery Network (CDN)**: For better performance and scalability, consider using a CDN (e.g., AWS CloudFront, Cloudflare) to serve static and media assets.

5.  **Database and Redis**:
    *   **Managed Services**: For production, consider using managed database (e.g., AWS RDS, Google Cloud SQL) and Redis services instead of running them in Docker containers on the same host. This offers better scalability, reliability, and manageability.
    *   **Backups**: Implement regular, automated backups for your PostgreSQL database.
    *   **Connection Pooling**: Ensure proper database connection pooling is configured (Gunicorn/Django settings or tools like PgBouncer if needed).

6.  **Celery Workers and Beat**:
    *   **Scaling**: Adjust the number of Celery worker processes (`-c` option) and potentially the number of worker service replicas based on load.
    *   **Monitoring**: Monitor Celery queues and task execution (e.g., using Flower or other monitoring tools).
    *   **Celery Beat Reliability**: If using `django-celery-beat` with a database backend, ensure the database is highly available. For critical scheduled tasks, consider alternative schedulers or ensure Beat has a robust restart policy and monitoring.

7.  **Logging and Monitoring**:
    *   **Centralized Logging**: Configure Docker to send container logs to a centralized logging system (e.g., ELK stack, Splunk, AWS CloudWatch Logs, Datadog).
    *   **Application Performance Monitoring (APM)**: Integrate an APM tool (e.g., Sentry, Datadog, New Relic) for error tracking and performance insights in Django and Celery.
    *   **Nginx Logs**: Ensure Nginx access and error logs are captured and monitored.

8.  **Scaling and Orchestration**:
    *   **Docker Compose in Production**: While `docker-compose` can be used for single-host deployments, for multi-host, scalable, and resilient deployments, consider container orchestration platforms like Kubernetes, Docker Swarm, or managed services like AWS ECS/EKS, Google GKE, Azure AKS.
    *   **Load Balancing**: If running multiple instances of `backend` or `nginx` services, a load balancer will be needed.

9.  **Build and Deployment Pipeline (CI/CD)**:
    *   Automate building Docker images, running tests, and deploying to staging/production environments using a CI/CD pipeline (e.g., Jenkins, GitLab CI, GitHub Actions, AWS CodePipeline).

10. **Resource Allocation**:
    *   Ensure sufficient CPU, memory, and disk space are allocated to your Docker host(s) and individual containers.

This list is not exhaustive but covers the most critical aspects when moving from the development setup described in this document to a live production environment. Each point often involves significant planning and configuration.

--- 