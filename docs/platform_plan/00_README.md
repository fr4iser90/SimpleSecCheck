# SecuLite v2 - Platform Development Plan

This directory contains all detailed planning documents for the development of SecuLite v2, a comprehensive, self-hosted security monitoring platform.

Our goal is to achieve a "mental finish" of the project plan – detailing architecture, database design, API structure, task breakdowns, UI/UX concepts, and Docker setup – before major coding commences.

## Planning Documents:

1.  **[01_architectural_decisions.md](01_architectural_decisions.md)**
    *   Records key architectural choices for the platform (backend framework, database, task queue, frontend approach, etc.).
    *   May link to more detailed Architectural Decision Records (ADRs) in a sub-directory.

2.  **[02_database_schema.md](02_database_schema.md)**
    *   Outlines the database models, entities, relationships (ERD concepts), and data types.

3.  **[03_api_design.md](03_api_design.md)**
    *   Describes the high-level design for the backend API, including key resource endpoints, request/response structures, and authentication mechanisms.

4.  **[04_task_breakdown_phase1.md](04_task_breakdown_phase1.md)**
    *   A detailed, actionable list of tasks for implementing "SecuLite v2 - Phase 1: Foundational Refactoring & Core Platform Development."
    *   May be further broken down into more granular task files.

5.  **[05_ui_ux_concepts_v1.md](05_ui_ux_concepts_v1.md)**
    *   Initial ideas, user stories, wireframes, or mockups for the new web dashboard and user interface.

6.  **[06_docker_setup_v2.md](06_docker_setup_v2.md)**
    *   Planning for the updated `Dockerfile` and `docker-compose.yml` required to support the new multi-service architecture (backend, database, task workers, frontend (if separate), reverse proxy, etc.).

7.  **[ADRs/](ADRs/)** (Architectural Decision Records) - *Optional Sub-directory*
    *   If we choose to use ADRs, this directory will store them.

## Related Top-Level Plans:

*   **[../PLAN.md](../PLAN.md):** High-level project roadmap for SecuLite v2 phases.
*   **[../detailed_plan.md](../detailed_plan.md):** Overall project vision, objectives, and evolved conceptual architecture.

---

*This plan is a living document and will be updated as decisions are made and details are fleshed out.* 