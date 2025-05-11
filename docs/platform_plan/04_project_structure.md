# SecuLite v2 - Project Directory Structure

This document outlines the proposed directory structure for the SecuLite v2 project, encompassing both the Django backend and the Vue.js frontend. The goal is to establish a clean, organized, and scalable structure.

## Table of Contents

1.  [Root Directory Structure](#1-root-directory-structure)
2.  [Backend (Django) Directory Structure (`backend/`)](#2-backend-django-directory-structure-backend)
    *   [2.1. Django Project (`seculite_api/`)](#21-django-project-seculite_api)
    *   [2.2. Django Apps (`apps/`)](#22-django-apps-apps)
3.  [Frontend (Vue.js) Directory Structure (`frontend/`)](#3-frontend-vuejs-directory-structure-frontend)
    *   [3.1. Vue.js Source (`src/`)](#31-vuejs-source-src)
4.  [Shared Docker Configuration](#4-shared-docker-configuration)
5.  [Justification and Conventions](#5-justification-and-conventions)

---

## 1. Root Directory Structure

```
seculite-v2/
├── backend/                  # Django backend application
├── frontend/                 # Vue.js frontend application
├── docs/
│   └── platform_plan/        # Planning documents (like this one)
│   └── ...                   # Other documentation (user guides, ADRs)
├── .dockerignore
├── .env.example              # Example environment variables
├── .gitignore
├── docker-compose.yml        # Docker Compose for local development and services
├── LICENSE
└── README.md                 # Main project README
```

---

## 2. Backend (Django) Directory Structure (`backend/`)

```
backend/
├── seculite_api/             # Django project configuration directory
│   ├── __init__.py
│   ├── asgi.py
│   ├── settings.py           # Main settings
│   ├── urls.py               # Root URL configurations
│   └── wsgi.py
├── apps/                     # Directory for individual Django applications (modules)
│   ├── users/
│   │   ├── migrations/
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── models.py         # UserProfile, Organization, OrganizationMembership
│   │   ├── serializers.py
│   │   ├── views.py          # API ViewSets/Views
│   │   ├── tests/
│   │   └── urls.py           # App-specific URLs
│   ├── projects/
│   │   ├── models.py         # Project, TargetAsset
│   │   └── ...               # (similar structure to users app)
│   ├── scans/
│   │   ├── models.py         # ScanConfiguration, Scan, ScanToolResult, Finding
│   │   ├── services/         # Business logic for scan orchestration
│   │   ├── tasks.py          # Celery tasks for scan execution
│   │   └── ...               # (similar structure to users app)
│   ├── tools/
│   │   ├── models.py         # ToolDefinition
│   │   ├──parsers/          # Parsers for different tool output formats
│   │   └── ...               # (similar structure to users app)
│   └── core/
│       ├── models.py         # Abstract base models, common fields/mixins
│       ├── permissions.py    # Custom DRF permission classes
│       ├── serializers.py    # Base serializers or common utility serializers
│       ├── utils.py          # Common utility functions
│       └── ...
├── staticfiles_collected/    # For collected static files in production (managed by Django)
├── media/                    # For user-uploaded files (e.g., ScanToolResult raw_output_path)
├── manage.py                 # Django's command-line utility
├── Dockerfile                # Dockerfile for the Django backend service
├── requirements.txt          # Python dependencies (or Pipfile/pyproject.toml for Poetry)
├── entrypoint.sh             # Script for Docker container startup (migrations, run server)
├── pytest.ini                # Pytest configuration (or other test runner config)
└── README.md                 # Backend-specific README
```

### 2.1. Django Project (`seculite_api/`)
This directory is created by `django-admin startproject`. It contains the main project-level configurations:
-   `settings.py`: Django settings for the project.
-   `urls.py`: Root URL dispatcher.
-   `wsgi.py` / `asgi.py`: Entry points for WSGI/ASGI compatible web servers.

### 2.2. Django Apps (`apps/`)
Each subdirectory within `apps/` represents a distinct Django application, promoting modularity:
-   **`users`**: Manages user accounts (`UserProfile`), organizations (`Organization`, `OrganizationMembership`), authentication, and authorization.
-   **`projects`**: Manages `Project` and `TargetAsset` entities.
-   **`scans`**: Manages `ScanConfiguration`, `Scan`, `ScanToolResult`, `Finding`. Also includes Celery tasks (`tasks.py`) and business logic for scan orchestration (`services/`).
-   **`tools`**: Manages `ToolDefinition` and includes logic for parsing tool outputs (`parsers/`).
-   **`core`**: Contains shared/common code: abstract base models, custom DRF permission classes, utility functions, etc., used across multiple apps.

Each app follows a standard Django app structure (`models.py`, `views.py`, `serializers.py`, `urls.py`, `admin.py`, `migrations/`, `tests/`).

---

## 3. Frontend (Vue.js) Directory Structure (`frontend/`)

```
frontend/
├── public/
│   ├── index.html
│   └── favicon.ico
├── src/
│   ├── assets/               # Static assets like images, fonts, global CSS
│   ├── components/
│   │   ├── common/           # General reusable UI components (buttons, modals, etc.)
│   │   └── specific/         # Components specific to features (e.g., FindingCard.vue)
│   ├── views/                # Page-level components (mapped to routes)
│   │   ├──DashboardView.vue
│   │   └──ProjectDetailView.vue
│   ├── router/               # Vue Router configuration (index.js)
│   ├── store/                # Pinia (or Vuex) state management (index.js, modules/)
│   ├── services/             # API service wrappers (e.g., projectService.js, authService.js)
│   ├── layouts/              # Main application layouts (e.g., DefaultLayout.vue, AuthLayout.vue)
│   ├── styles/               # Global styles, variables, mixins (e.g., main.scss)
│   ├── utils/                # Frontend utility functions (formatters, validators)
│   ├── App.vue               # Root Vue component
│   └── main.js               # Main entry point for the Vue application
├── .env.development
├── .env.production
├── .eslintrc.js              # ESLint configuration
├── .prettierrc.json          # Prettier configuration
├── Dockerfile                # Dockerfile for the Vue.js frontend (e.g., for Nginx serving)
├── vite.config.js            # Vite configuration (or vue.config.js for Vue CLI)
├── package.json
├── yarn.lock (or package-lock.json)
└── README.md                 # Frontend-specific README
```

### 3.1. Vue.js Source (`src/`)
-   **`assets/`**: Static assets that are part of the build process.
-   **`components/`**: Reusable Vue components, possibly organized into `common/` and feature-specific subdirectories.
-   **`views/`**: Components that represent entire pages, mapped by Vue Router.
-   **`router/`**: Vue Router configuration, defining application routes.
-   **`store/`**: Pinia (recommended for Vue 3) or Vuex for global state management.
-   **`services/`**: Modules responsible for making API calls to the backend (e.g., using Axios).
-   **`layouts/`**: Components that define the overall structure of pages (e.g., with headers, footers, sidebars).
-   **`styles/`**: Global SASS/CSS files, variables, mixins.
-   **`App.vue`**: The root Vue component.
-   **`main.js`**: The application's entry point where Vue is initialized with plugins, router, store, etc.

---

## 4. Shared Docker Configuration

-   **`docker-compose.yml`**: Defines the services for local development (backend, frontend, PostgreSQL, Redis, Celery worker, Celery beat, Nginx for serving frontend).
-   **`.env.example`**: Provides a template for environment variables needed by `docker-compose.yml` and the applications (e.g., database credentials, secret keys, API URLs).
-   **`.dockerignore`**: Specifies files and directories to ignore when building Docker images.

---

## 5. Justification and Conventions

-   **Separation of Concerns:** Backend and frontend are clearly separated into their own top-level directories.
-   **Modularity (Django):** The `apps/` directory in the backend encourages breaking down functionality into smaller, manageable Django apps.
-   **Modularity (Vue):** The `src/` structure in the frontend promotes organization by feature or type (components, views, services, store).
-   **Standard Practices:** Adheres to common conventions for Django and Vue.js projects.
-   **Dockerization:** Includes Dockerfiles for individual services and a `docker-compose.yml` for orchestration, facilitating consistent development and deployment environments.
-   **Configuration Management:** Use of `.env` files for environment-specific configurations.

--- 