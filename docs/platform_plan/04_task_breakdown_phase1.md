# SecuLite v2 - Phase 1 Task Breakdown (MVP)

**Version:** 1.0
**Date:** $(date +%Y-%m-%d)
**Source Documents:** `docs/platform_plan/09_mvp_epics_user_stories.md`, `docs/platform_plan/07_feature_backlog.md` (P0 features)

This document outlines the high-level tasks for implementing the SecuLite v2 Minimum Viable Product (MVP), corresponding to "Phase 1: Foundational Refactoring & Core Platform Development." Tasks are grouped by the Epics defined in `09_mvp_epics_user_stories.md`. Further granulation will occur as development progresses.

## General Setup Tasks (Prerequisites)

-   **G1. Project Initialization**:
    -   G1.1. Initialize Django project (`seculite_api`) as per `04_project_structure.md`.
    -   G1.2. Initialize Vue.js project (`frontend`) as per `04_project_structure.md`.
    -   G1.3. Set up Docker environment as per `05_docker_setup.md` (PostgreSQL, Redis, Backend, Nginx).
    -   G1.4. Implement initial CI/CD pipeline basics as per `06_ci_cd_pipeline.md` (linting, basic tests).
-   **G2. Core Django App Setup**:
    -   G2.1. Create `core` Django app for shared models, utilities, permissions.
    -   G2.2. Implement base abstract models (e.g., `TimestampedModel`).

## Epic 1: Core User Authentication & Authorization

-   **E1.1. User Model Setup**:
    -   E1.1.1. Create `users` Django app.
    -   E1.1.2. Define `UserProfile` model extending Django `User` (API keys, notification prefs placeholder, timezone) as per `02_data_model_and_db_schema.md`.
    -   E1.1.3. Define `Organization` and `OrganizationMembership` models (initially for structure, full multi-tenancy for non-MVP if confirmed later).
    -   E1.1.4. Implement serializers for `User`, `UserProfile`.
-   **E1.2. Authentication API Endpoints**:
    -   E1.2.1. Implement user registration endpoint (`/auth/registration/`).
    -   E1.2.2. Implement user login endpoint (`/auth/login/`) (session and token).
    -   E1.2.3. Implement user logout endpoint (`/auth/logout/`).
    -   E1.2.4. Implement password reset request (`/auth/password/reset/`) and confirmation (`/auth/password/reset/confirm/`) endpoints.
    -   E1.2.5. Implement password change endpoint (`/auth/password/change/`).
-   **E1.3. User Profile API Endpoints**:
    -   E1.3.1. Implement current user detail endpoints (`/auth/user/`, `/auth/userprofile/`) (GET, PUT, PATCH).
    -   E1.3.2. Implement API key management for `UserProfile` (`/auth/userprofile/api-key/`).
-   **E1.4. Authorization & RBAC (Basic)**:
    -   E1.4.1. Define initial roles (Admin, User placeholders) and basic DRF permission classes.
    -   E1.4.2. Secure core endpoints with `IsAuthenticated` and basic role checks.
-   **E1.5. Frontend Authentication UI**:
    -   E1.5.1. Create Vue.js views for Registration, Login, Password Reset.
    -   E1.5.2. Implement Vue.js store (Pinia) modules for auth state.
    -   E1.5.3. Implement API service calls for auth endpoints.
    -   E1.5.4. Create User Profile view (view/edit profile, manage API key).
-   **E1.6. Security Features**:
    -   E1.6.1. Implement password complexity rules (Django validator).
    -   E1.6.2. Implement account lockout logic (e.g., using `django-axes` or custom middleware).

## Epic 2: Project & System Foundation

-   **E2.1. Project Model Setup**:
    -   E2.1.1. Create `projects` Django app.
    -   E2.1.2. Define `Project` model as per `02_data_model_and_db_schema.md`.
    -   E2.1.3. Define `TargetAsset` model.
    -   E2.1.4. Implement serializers for `Project`, `TargetAsset`.
-   **E2.2. Project CRUD API Endpoints**:
    -   E2.2.1. Implement API endpoints for `Project` (List, Create, Retrieve, Update, Delete).
    -   E2.2.2. Implement nested API endpoints for `TargetAsset` under projects.
-   **E2.3. Central Dashboard (Basic)**:
    -   E2.3.1. Create basic Django view/template or API endpoint for dashboard data.
    -   E2.3.2. Create basic Vue.js view for the dashboard (placeholder for metrics).
-   **E2.4. System Settings (Basic)**:
    -   E2.4.1. Define model for basic system settings (e.g., SMTP config).
    -   E2.4.2. Create Django admin interface for managing these settings.
    -   E2.4.3. Implement API endpoint for admin to manage system settings.

## Epic 3: Scan Setup & Configuration

-   **E3.1. ToolDefinition Model Setup**:
    -   E3.1.1. Create `tools` Django app.
    -   E3.1.2. Define `ToolDefinition` model as per `02_data_model_and_db_schema.md`.
    -   E3.1.3. Implement serializer for `ToolDefinition`.
    -   E3.1.4. Populate initial `ToolDefinition` entries (e.g., Bandit, ESLint, Trivy, Gitleaks).
-   **E3.2. ScanConfiguration Model Setup**:
    -   E3.2.1. Create `scans` Django app.
    -   E3.2.2. Define `ScanConfiguration` model.
    -   E3.2.3. Implement serializer for `ScanConfiguration`.
-   **E3.3. Scan Configuration API Endpoints**:
    -   E3.3.1. Implement API endpoints for `ScanConfiguration` (List, Create, Retrieve, Update, Delete, Clone), nested under projects.
    -   E3.3.2. Implement API endpoint to list available `ToolDefinition`s.
-   **E3.4. Frontend Scan Configuration UI**:
    -   E3.4.1. Create Vue.js views for listing, creating, and editing `ScanConfiguration`s.
    -   E3.4.2. UI to select `TargetAsset`s and `ToolDefinition`s for a configuration.
    -   E3.4.3. UI for basic scheduling options (one-time, recurring).

## Epic 4: Scan Execution & Monitoring

-   **E4.1. Scan Model Setup**:
    -   E4.1.1. Define `Scan` model.
    -   E4.1.2. Define `ScanToolResult` model.
    -   E4.1.3. Implement serializers for `Scan`, `ScanToolResult`.
-   **E4.2. Scan Execution Logic (Celery)**:
    -   E4.2.1. Set up Celery in Django project.
    -   E4.2.2. Create Celery task for initiating a scan from a `ScanConfiguration`.
    -   E4.2.3. Create Celery task for executing a single tool (placeholder for actual tool execution logic).
    -   E4.2.4. Implement logic to update `Scan` and `ScanToolResult` status.
-   **E4.3. Scan API Endpoints**:
    -   E4.3.1. Implement API endpoint to launch a scan from a `ScanConfiguration`.
    -   E4.3.2. Implement API endpoints for `Scan` (List, Retrieve, Cancel).
    -   E4.3.3. Implement nested API endpoints for `ScanToolResult` under scans.
-   **E4.4. Frontend Scan Monitoring UI**:
    -   E4.4.1. Create Vue.js views for listing scans and viewing scan details (status, progress).
    -   E4.4.2. UI to manually launch and cancel scans.

## Epic 5: Tool Integration Backbone

-   **E5.1. Tool Runner Service**:
    -   E5.1.1. Design and implement a basic service/module within `scans` app to run tools (CLI/Docker).
    -   E5.1.2. Integrate initial tools:
        -   Bandit (SAST) wrapper.
        -   ESLint (Linting) wrapper.
        -   Trivy (SCA for containers - basic local image scan or dummy).
        -   Gitleaks (Secrets - basic local repo scan or dummy).
-   **E5.2. Result Parsing**:
    -   E5.2.1. Implement basic parsers for the output of initial tools to extract findings into a standardized format.
    -   E5.2.2. Map tool-specific severity to internal standardized scale.

## Epic 6: Findings Lifecycle Management (MVP Core)

-   **E6.1. Finding Model Setup**:
    -   E6.1.1. Define `Finding` model as per `02_data_model_and_db_schema.md`.
    -   E6.1.2. Implement serializer for `Finding`.
-   **E6.2. Finding Ingestion Logic**:
    -   E6.2.1. Implement logic to create/update `Finding` records from parsed tool results.
    -   E6.2.2. Implement basic deduplication logic for findings.
-   **E6.3. Finding API Endpoints**:
    -   E6.3.1. Implement API endpoints for `Finding` (List, Retrieve, Update for triage - status, assignee).
    -   E6.3.2. Implement basic filtering for findings (project, scan, severity, status).
-   **E6.4. Frontend Findings UI**:
    -   E6.4.1. Create Vue.js views for listing findings.
    -   E6.4.2. Create Vue.js view for detailed finding information.
    -   E6.4.3. Implement UI for basic triage actions (change status, assign).

## Epic 7: Basic Reporting & Export (MVP)

-   **E7.1. Scan Summary Report**:
    -   E7.1.1. Implement API endpoint to generate data for a scan summary report.
    -   E7.1.2. Create Vue.js component to display scan summary.
-   **E7.2. Finding Export**:
    -   E7.2.1. Implement API endpoint to export findings for a scan/project in CSV.
    -   E7.2.2. Implement API endpoint to export findings for a scan/project in JSON.
    -   E7.2.3. Add buttons in UI to trigger these exports.

## Epic 8: Core Notification System (MVP)

-   **E8.1. Notification Logic**:
    -   E8.1.1. Implement Django signals or direct calls for scan completion, new high/critical findings, and finding assignment.
    -   E8.1.2. Implement email sending functionality (using Django's email system and SMTP settings).
-   **E8.2. User Notification Preferences (Basic)**:
    -   E8.2.1. Add fields to `UserProfile` for basic email notification toggles (e.g., scan complete, new critical finding).
    -   E8.2.2. Update `UserProfile` API and UI to manage these preferences.

## Epic 9: System Administration Basics (MVP)

-   **E9.1. User Management UI (Django Admin)**:
    -   E9.1.1. Configure Django admin for `User`, `UserProfile`, `Organization`, `OrganizationMembership`.
    -   E9.1.2. Implement actions in Django admin for inviting users (placeholder/basic), (de)activating accounts, assigning roles.
-   **E9.2. Admin Password Reset**:
    -   E9.2.1. Ensure admin can trigger password reset for users (e.g., via Django admin).
-   **E9.3. Global System Settings UI (Django Admin)**:
    -   E9.3.1. Configure Django admin for system settings model (SMTP, default email 'from').

## Epic 10: Foundational User Experience (MVP - Guiding Principles)

-   **E10.1. UI/UX Implementation**:
    -   E10.1.1. Apply UX principles (intuitive navigation, clear feedback, sensible defaults) across all implemented MVP frontend features.
    -   E10.1.2. Ensure basic responsiveness for desktop.
    -   E10.1.3. Implement user-friendly forms and validation.

## Epic 11: Core Platform Security (MVP - Guiding Principles & Features)

-   **E11.1. Security Implementation**:
    -   E11.1.1. Adhere to secure coding practices during all development.
    -   E11.1.2. Implement robust input validation and output encoding for all user inputs and API responses.
    -   E11.1.3. Ensure secure handling of secrets (Django `SECRET_KEY`, DB credentials via .env).
    -   E11.1.4. Ensure API endpoints enforce authN/authZ.
    -   E11.1.5. Enable and verify Django's built-in CSRF protection.
    -   E11.1.6. Set up basic SAST/SCA scans for the platform's own codebase in CI/CD.

## Epic 12: Essential Developer & Release Documentation (MVP)

-   **E12.1. Development Environment Setup Guide**:
    -   E12.1.1. Create `docs/developer_setup.md` detailing local environment setup using Docker.
-   **E12.2. Release Notes / Changelog**:
    -   E12.2.1. Create initial `CHANGELOG.md` or `RELEASE_NOTES.md` file.
    -   E12.2.2. Establish process for updating changelog with each significant change/PR.

## Epic 13: Docker Host Integration for Target Definition (New)

**Goal:** Enable users to select codebases from Docker containers running locally on the server as scan targets.

-   **E13.1. Backend: Docker API Interaction & Configuration**:
    -   E13.1.1. Add `docker-py` (Python Docker library) to backend dependencies (`pyproject.toml`).
    -   E13.1.2. Update `docker-compose.yml` to mount the host's Docker socket (`/var/run/docker.sock`) into the backend container (reference: `05_docker_setup.md`). Document security implications.
    -   E13.1.3. Implement service logic in the backend to list running containers and inspect their volume mounts via the Docker API.
    -   E13.1.4. Develop and implement heuristics to identify potentially relevant host paths for codebases from volume mounts.
-   **E13.2. Backend: New API Endpoints for Docker Host Interaction**:
    -   E13.2.1. Implement API endpoint `/api/v1/dockerhost/containers/` (List Running Docker Containers) as per `03_api_design.md`.
        -   Include filtering by name and status.
        -   Ensure endpoint is restricted to authorized users (e.g., Admins).
    -   E13.2.2. Implement API endpoint `/api/v1/dockerhost/containers/{container_id}/code-paths/` (Retrieve Potential Code Paths) as per `03_api_design.md`.
        -   Ensure endpoint is restricted to authorized users.
    -   E13.2.3. Write unit and integration tests for the new API endpoints and Docker interaction logic.
-   **E13.3. Frontend: UI for Docker Container Selection in Project Creation/Editing**:
    -   E13.3.1. Design and implement UI elements in `ProjectCreateModal.vue` (or a dedicated component) to:
        -   Display an option/button to "Select codebase from local Docker container" (visible to authorized users only).
        -   Display a list of running Docker containers (fetched from the new API endpoint).
        -   Provide filtering capabilities for the container list.
    -   E13.3.2. On container selection, implement an API call to fetch potential code paths for that container.
    -   E13.3.3. Display a selection for the host paths provided by the backend.
    -   E13.3.4. Populate the selected host path into the project form's "Codebase Path or URL" (`codebase_path_or_url`) field.
    -   E13.3.5. Store metadata (e.g., container name, path in container) in the `TargetAsset`'s (or project's default configuration) `metadata` field when the project is created.
-   **E13.4. Frontend: Backend API Integration**:
    -   E13.4.1. Create API service functions in the frontend to communicate with the new `/api/v1/dockerhost/...` endpoints.
    -   E13.4.2. Adapt frontend state management (Pinia/Vuex) to handle fetched container and path data if necessary.
    -   E13.4.3. Implement error handling for API calls.
-   **E13.5. Documentation & Tests**:
    -   E13.5.1. Describe the new functionality in user and administrator documentation.
    -   E13.5.2. Create end-to-end tests for the "create project with codebase from Docker container" workflow (if E2E tests are within MVP scope).

This task breakdown provides a high-level roadmap. Each task will be further broken down into smaller, more manageable sub-tasks and potentially issues in a project tracking system as development commences. 