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
*(Placeholder for PostgreSQL service details: image, volumes, env_file, ports, networks)*

### 3.2. `redis` Service
*(Placeholder for Redis service details: image, ports, networks, volumes)*

### 3.3. `backend` (Django) Service
*(Placeholder for Django backend service details: build context, entrypoint, volumes, ports, env_file, depends_on, networks)*

### 3.4. `worker` (Celery Worker) Service
*(Placeholder for Celery worker service details: build context (same as backend), command, env_file, depends_on, networks)*

### 3.5. `beat` (Celery Beat) Service
*(Placeholder for Celery beat service details: build context (same as backend), command, env_file, depends_on, networks)*

### 3.6. `frontend` (Vue.js Build Stage - in Dockerfile)
*(This is not a separate service in `docker-compose.yml` but part of the `nginx` service's build process or a multi-stage build within `frontend/Dockerfile` whose output is used by `nginx`.)*

### 3.7. `nginx` (Web Server/Reverse Proxy) Service
*(Placeholder for Nginx service details: image (official or custom build), volumes (for nginx.conf and frontend static assets), ports, depends_on, networks)*

### 3.8. Volumes
*(Placeholder for named volume definitions: `postgres_data`, `redis_data`, potentially `backend_static_collected`, `backend_media_data`)*

### 3.9. Networks
*(Placeholder for custom network definition: `seculite_network`)*

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