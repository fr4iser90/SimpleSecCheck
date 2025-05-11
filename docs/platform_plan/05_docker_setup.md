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

*(This section will detail the steps: base Python image, working directory, environment variables like `PYTHONUNBUFFERED`, installing dependencies from `requirements.txt`, copying app code, and user setup. CMD or ENTRYPOINT will refer to `entrypoint.sh`.)*

---

## 5. `backend/entrypoint.sh` Details

*(This script will handle: waiting for DB to be ready (optional), applying Django migrations, collecting static files, and starting Gunicorn/Daphne. Example commands will be provided.)*

---

## 6. `frontend/Dockerfile` Details (Multi-stage)

*(This section will describe a multi-stage Dockerfile: Stage 1 (builder) using a Node image to install dependencies and build the Vue.js app. Stage 2 using an Nginx image to copy built assets from Stage 1 and the Nginx configuration.)*

---

## 7. `nginx/nginx.conf` Details (Example for `nginx` service)

*(This section will provide an example Nginx configuration: upstream definition for the backend, server block for port 80/443, location block for serving frontend static assets from `/var/www/frontend`, location block for proxying `/api/` requests to the backend service, SSL configuration placeholders, and basic security headers.)*

---

## 8. Environment Variables (`.env.example`)

*(A comprehensive list of necessary environment variables will be provided here, covering database credentials, Django settings, Celery settings, API URLs, etc. This will serve as a template for the actual `.env` file.)*

---

## 9. Development Workflow Considerations

-   Using `docker-compose up --build`.
-   Volume mounts for live code reloading (backend Python and frontend Vue.js).
-   Accessing services (e.g., frontend via Nginx at `http://localhost:80`, backend API via Nginx proxy).
-   Debugging individual services.

---

## 10. Production Deployment Considerations (Brief)

-   Differences from development (e.g., no code volume mounts for backend/frontend, robust SSL, secrets management, logging, scaling services).
-   Serving static and media files (Django `collectstatic`, Nginx serving media/static or using a CDN).

--- 