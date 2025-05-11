# SecuLite Platform: Detailed Project Plan

## 1. Project Overview & Objectives
SecuLite is evolving from a script-based security toolkit into a comprehensive, self-hosted security monitoring platform. It aims to provide continuous, automated security anlaysis for multiple targets (web applications, code repositories, services), featuring a rich web interface for management and reporting, a robust database backend for historical data and trend analysis, and advanced LLM integration for vulnerability insights and potential remediation suggestions.

**Core Objectives (SecuLite Platform):**
-   **Centralized Multi-Target Monitoring:** Allow users to define, configure, and monitor multiple scan targets (URLs, codebases, container images) from a single platform.
-   **Automated & Scheduled Scanning:** Support both on-demand and scheduled security scans for all configured targets.
-   **Comprehensive Security Analysis:** Integrate and orchestrate various security tools (ZAP, Semgrep, Trivy, and potentially others) to cover web vulnerabilities, static code analysis (including AI/LLM specific issues and secrets), and dependency/container vulnerabilities.
-   **Rich Web Interface:** Provide an intuitive and interactive dashboard for:
    *   Managing scan targets and configurations.
    *   Initiating and monitoring scans.
    *   Visualizing scan results, trends, and historical data.
    *   Managing user accounts and platform settings.
-   **Database Backend:** Implement a robust database (e.g., PostgreSQL) to store:
    *   User accounts and platform configurations.
    *   Scan target definitions and specific configurations.
    *   Historical scan results, findings, and their states (new, acknowledged, resolved).
    *   LLM interaction logs and analysis outputs.
-   **Advanced LLM Integration:** Move beyond simple explanations to:
    *   Provide deeper contextual analysis of vulnerabilities.
    *   Offer more detailed and actionable remediation advice.
    *   Potentially assist in generating "auto-fix" suggestions or code patches.
    *   Support querying scan data using natural language.
-   **User Authentication & Authorization:** Secure the platform with user accounts and role-based access control.
-   **Scalability & Maintainability:** Design the platform with a modular architecture that is scalable to handle a growing number of targets and users, and is maintainable over time.
-   **Extensibility:** Allow for future integration of new scanning tools, rule sets, and reporting modules.

---

## 2. Tech Stack Selection (Evolved for Platform)

**Core Scanning Engines (To be integrated):**
-   **OWASP ZAP:** Web vulnerability scanning (DAST).
-   **Semgrep:** Static code analysis (SAST - code, AI, secrets).
-   **Trivy:** Dependency and container scanning (SCA).
-   **Shell (Bash) Scripts:** Will still be used for individual tool execution, but orchestrated by the backend.

**Platform Backend & Infrastructure:**
-   **Backend Framework:** *To be decided (e.g., Django, FastAPI, enhanced Flask with ORM & Blueprints).* Rationale: Need a framework that supports robust API development, database interaction, user authentication, and can manage complex workflows.
-   **Database:** *To be decided (e.g., PostgreSQL, MySQL/MariaDB).* Rationale: Relational database for structured data, historical trends, and user management. PostgreSQL is favored for its robustness and feature set.
-   **Task Queue / Message Broker:** *To be decided (e.g., Celery with Redis or RabbitMQ).* Rationale: Essential for managing asynchronous, long-running scan tasks without blocking the web interface.
-   **Web Server / ASGI/WSGI Server:** (e.g., Gunicorn, Uvicorn, Nginx as a reverse proxy). Rationale: Production-grade serving of the backend application.

**Platform Frontend:**
-   **JavaScript Framework (Potential):** *To be decided if a full SPA is desired (e.g., React, Vue, Svelte).* Rationale: For a highly interactive and complex dashboard, a modern JS framework might be more suitable than server-side templating alone. Otherwise, enhanced server-side templating with JavaScript for dynamic components.
-   **HTML, CSS, JavaScript:** Core web technologies for the user interface.

**Configuration & Rules:**
-   **YAML:** For Semgrep rules, Trivy configurations, and potentially application configurations.
-   **JSON:** For data interchange, API request/responses.

**CI/CD & Version Control:**
-   **Git & GitHub/GitLab:** For version control and CI/CD pipelines.
-   **Docker & Docker Compose:** For containerization, development, and deployment consistency.

**Rationale for New Components:**
The shift to a platform model requires robust solutions for data persistence, asynchronous task handling, API development, and a more sophisticated user interface, necessitating the consideration of dedicated frameworks and tools for these purposes.

---

## 3. Architecture Overview (Platform Model)

The SecuLite platform will transition from a script-centric model to a modern web application architecture.

```
+---------------------+      +------------------------+      +-----------------------+
|     Web Browser     | <--> |  Frontend Application  | <--> |   Backend API Server  |
| (User Interface)    |      | (React/Vue/Svelte/HTML)|      | (Django/FastAPI/Flask)|
+---------------------+      +------------------------+      +----------+------------+
                                                                         | (REST/GraphQL)
                                                                         v
+---------------------------------------+      +-----------------------+      +-------------------------+
|         Background Task Queue         | <--> |  Scanning Orchestrator| <--> |   Individual Scanners   |
| (Celery, Redis/RabbitMQ)              |      | (Backend Logic)       |      | (ZAP, Semgrep, Trivy via|
+---------------------------------------+      +----------+------------+      |  adapted shell scripts) |
                                                          |                     +-------------------------+
                                                          v
                                                +-----------------------+
                                                |       Database        |
                                                | (PostgreSQL/MySQL)    |
                                                | - Scan Configs & Targets|
                                                | - Historical Results  |
                                                | - User Accounts       |
                                                | - LLM Interactions    |
                                                +-----------------------+
                                                          ^
                                                          | (Data Storage & Retrieval)
                                                          |
                                                +-----------------------+
                                                |    LLM Service/API    |
                                                | (OpenAI, Gemini, etc.)|
                                                +-----------------------+

```

**Key Architectural Components:**

1.  **Frontend Application:** The user-facing web interface. This could be a Single Page Application (SPA) built with a modern JavaScript framework or a server-side rendered application with dynamic JavaScript components. It communicates with the Backend API.
2.  **Backend API Server:** The core logic of the platform. It exposes RESTful or GraphQL APIs for the frontend to consume. Responsibilities include:
    *   User authentication and authorization.
    *   Managing scan targets, configurations, and schedules.
    *   Receiving scan initiation requests and dispatching them to the Background Task Queue.
    *   Retrieving and formatting scan results from the Database for the frontend.
    *   Interacting with the LLM Service.
3.  **Database:** Stores all persistent data for the platform.
4.  **Background Task Queue:** Manages asynchronous execution of security scans. The Backend API server places scan jobs on the queue, and worker processes pick them up.
5.  **Scanning Orchestrator (part of Backend Logic / Workers):** This component, triggered by the task queue, is responsible for:
    *   Fetching scan configurations for a given target.
    *   Invoking the appropriate individual scanner scripts (adapted versions of `run_zap.sh`, `run_semgrep.sh`, `run_trivy.sh`) with the correct parameters and environment.
    *   Collecting results from the scanners.
    *   Parsing and storing results in the Database.
6.  **Individual Scanners:** The existing tool scripts, refactored to be callable by the Scanning Orchestrator and to output results in a structured way that can be easily parsed and stored.
7.  **LLM Service/API:** Handles communication with external Large Language Models for analysis, explanations, and suggestions.

---

## 4. Folder & File Structure (Anticipated Evolution)
The current structure will need to evolve to accommodate a full web application. Example (conceptual):

-   `/app/` or `/seculite_platform/` - Main backend application code
    -   `/api/` - API endpoints/views
    -   `/scanners/` - Logic for orchestrating individual scan tools
    -   `/tasks/` - Celery tasks for background scanning
    -   `/models/` - Database models (ORM definitions)
    -   `/auth/` - Authentication and authorization logic
    -   `/static/` - Backend static files (if any)
    -   `/templates/` - Backend HTML templates (if not a full SPA)
-   `/frontend/` - (If SPA) Frontend application code (React, Vue, etc.)
-   `/scripts/tools/` - Existing (and adapted) individual tool scripts (`run_zap.sh`, etc.)
-   `/rules/` — Semgrep and custom rules (as is)
-   `/config/` - Platform configuration files
-   `/migrations/` - Database migration scripts
-   `/tests/` - Automated tests for backend and frontend
-   `/docs/` — Project documentation (as is, but expanded)
-   `docker-compose.yml`, `Dockerfile` - Updated for the new services
-   `.env` - Environment variables

---

## 5. Implementation Phases (SecuLite Platform)

Corresponds to the updated `PLAN.md`:

1.  **Phase 1: Foundational Refactoring & Core Platform Development**
    *   Detailed architectural decisions (Backend framework, DB, Task Queue).
    *   Setup core backend project structure.
    *   Implement basic database schema and ORM.
    *   Develop core user authentication.
    *   Implement basic multi-target definition and storage.
    *   Integrate task queue for asynchronous scan initiation (proof of concept).
    *   Adapt one scanner (e.g., Semgrep) to be callable by the backend via the task queue and store basic results.
    *   Basic API endpoints for target management and scan initiation.
    *   Start foundational work for the new web dashboard framework (e.g., serving a basic SPA shell or setting up server-side project structure).
2.  **Phase 2: Advanced Scanning & Reporting**
    *   Integrate all existing scanners (ZAP, Trivy) into the new backend orchestration.
    *   Implement automated periodic/scheduled scanning.
    *   Develop advanced vulnerability correlation and deduplication logic.
    *   Build initial reporting features in the new dashboard (listing targets, scans, basic findings).
    *   Schema enhancements for historical data and trend analysis.
3.  **Phase 3: Full UI/UX Implementation**
    *   Complete the interactive web dashboard with rich visualizations.
    *   Implement scan scheduling and advanced configuration options via UI.
    *   User management interface.
    *   Detailed finding views with history and status tracking.
4.  **Phase 4: Auto-Fix & Deeper AI Integration**
    *   Explore and implement "auto-fix" suggestions or semi-automated remediation for select vulnerabilities.
    *   Deeper LLM integration for proactive threat modeling, advanced natural language querying of findings, and adaptive learning from user feedback on findings.
5.  **Phase 5: Enterprise Features & Polish**
    *   Team collaboration features, role-based access control (RBAC) enhancements.
    *   SSO integration options.
    *   Compliance mapping and reporting (OWASP Top 10, CIS Benchmarks, etc.).
    *   Extensive documentation, professional polish, and refined onboarding.

---

## 6. Task Breakdown & Sequencing
-   Existing `task_*.md` files will need to be reviewed. Many completed tasks relate to the current script-based system.
-   New, detailed task lists will be created for each module of SecuLite v2 (e.g., `task_db_setup.md`, `task_auth_impl.md`, `task_api_targets.md`, `task_celery_setup.md`, `task_frontend_dashboard_v1.md`, etc.) corresponding to the new phases.

---

## 7. Documentation & Extension Guidelines
-   All platform features, API endpoints, architecture, and extension points will be thoroughly documented in the `/docs` directory, linked from `INDEX.md`.
-   Guidelines for adding new scanning tools, extending the database schema, and contributing to the frontend/backend will be created.

---

## 8. CI/CD & Automation Strategy
-   `docker-compose.yml` will be updated to manage the multiple services (backend, frontend, database, task workers, reverse proxy).
-   GitHub Actions (or GitLab CI) will be used for automated testing, building Docker images, and potentially deployment.

---

## 9. Testing & Validation Plan
-   Unit tests for backend logic, API endpoints, and helper functions.
-   Integration tests for interactions between services (API, task queue, database).
-   End-to-end tests for key user flows (defining a target, running a scan, viewing results).
-   Security testing of the SecuLite platform itself.
-   User Acceptance Testing (UAT) for dashboard usability and features.

---

## 10. Roadmap & Future Work (Platform Vision)
This section will now reflect the "SecuLite v2 - Subsequent Phases" and "Longer-Term Vision" from the updated `PLAN.md`. Key items include:
-   Advanced vulnerability management (correlation, deduplication, lifecycle tracking).
-   Sophisticated reporting and analytics (trends, compliance dashboards).
-   Enhanced LLM capabilities (auto-fix, proactive threat modeling, natural language querying).
-   Plugin architecture for new tools and custom checks.
-   SIEM integration.
-   Community features.
-   Self-healing capabilities.
