# SecuLite Project Plan (Autonomous Roadmap)

## Current State
- All-in-one security toolkit (ZAP, Semgrep, Trivy) is robust and CI/CD-ready.
- ZAP report persistence is solved with a fallback copy mechanism.
- Roles/rules are streamlined for autonomous, self-improving management.
- Basic dashboard with scan button and status is implemented via `security-summary.html` and `webui.js`.

## SecuLite v2 - Phase 1: Foundational Refactoring & Core Platform Development
This phase focuses on building the core backend and infrastructure for SecuLite as a monitoring platform.

1.  **Define and Implement Backend Architecture:**
    *   Select and implement a robust backend framework (e.g., Django, FastAPI, or significantly enhanced Flask).
    *   Design a scalable and maintainable project structure.
2.  **Database Integration:**
    *   Design a database schema (e.g., using PostgreSQL) to store:
        *   Scan targets (multiple services, repositories, URLs).
        *   Historical scan results and findings.
        *   User accounts and configurations.
        *   LLM interaction logs.
    *   Implement ORM and migration strategies.
3.  **User Authentication & Authorization:**
    *   Implement a secure user registration and login system.
    *   Define roles and permissions for accessing different platform features.
4.  **Multi-Target Scanning Engine:**
    *   Design and implement the capability to define and manage multiple scan targets.
    *   Adapt existing scan scripts (`run_zap.sh`, `run_semgrep.sh`, `run_trivy.sh`) to be callable by the new backend for specific targets.
5.  **Background Task Management:**
    *   Integrate a task queue system (e.g., Celery with Redis/RabbitMQ) for handling asynchronous and potentially long-running security scans.
6.  **New Web Dashboard - Initial Framework:**
    *   Begin development of a new, comprehensive web UI/UX.
    *   Focus on API-driven interactions with the backend.
    *   Plan for target management, scan initiation, and basic results visualization.
7.  **Enhanced LLM Integration Framework:**
    *   Develop a more robust service for LLM interactions, supporting configurable providers and more complex analysis tasks beyond basic explanations.

## SecuLite v2 - Subsequent Phases (High-Level)
- **Phase 2: Advanced Scanning & Reporting:**
    *   Automated periodic scanning of configured targets.
    *   Advanced vulnerability correlation and deduplication.
    *   Comprehensive and customizable reporting features (trends, compliance).
- **Phase 3: Full UI/UX Implementation:**
    *   Complete the interactive web dashboard with rich visualizations, scan scheduling, user management, and configuration options.
- **Phase 4: Auto-Fix & Deeper AI Integration:**
    *   Explore and implement "auto-fix" suggestions or semi-automated remediation.
    *   Deeper LLM integration for proactive threat modeling, advanced query capabilities, and adaptive learning.
- **Phase 5: Enterprise Features & Polish:**
    *   Team collaboration features, SSO integration, advanced RBAC.
    *   Compliance mapping (OWASP Top 10, CIS Benchmarks, etc.).
    *   Extensive documentation, professional polish, and onboarding.

## Longer-Term Vision (Beyond Core SecuLite v2)
- Integration with Security Information and Event Management (SIEM) systems.
- Community-driven rule sharing and threat intelligence feeds.
- Support for a wider array of security tools and scanners through a plugin architecture.
- Self-healing capabilities for certain types of vulnerabilities.

## Self-Monitoring
- This plan will be updated after each major architectural decision and phase completion.
- See also: `STATUS.md` for current progress and `detailed_plan.md` for architectural specifics. 