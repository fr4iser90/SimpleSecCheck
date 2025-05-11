# SecuLite v2: MVP Feature List

**Version:** 1.0
**Date:** $(date +%Y-%m-%d)
**Source Document:** `docs/platform_plan/07_feature_backlog.md`

This document lists all features designated as **P0 (MVP - Must-Have for Minimum Viable Product)** for SecuLite v2. These are the core, critical features essential for the first usable and valuable version of the platform.

## 1. Core Platform & Infrastructure (P0)

-   User Authentication (Registration, Login, Logout, Password Reset)
    -   Password Complexity Rules & Account Lockout (after multiple failed attempts)
-   User Authorization & Role-Based Access Control (RBAC - e.g., Admin, Project Owner, Project Member, Auditor)
-   Project Management (Create, Read, Update, Delete Projects by authorized users)
-   Robust API Infrastructure (as defined in `03_api_design.md`)
-   Central Dashboard/Overview Page (Key metrics, recent activity, assigned tasks)
-   User Profile Management (View/edit own profile, API key management for users)
-   System Settings Management (For administrators: e.g., mail server, default configurations, SMTP server)

## 2. Scan Configuration & Execution (P0)

-   Scan Configuration Management (Create, Read, Update, Delete configurations).
    -   Scan configurations to include: name, description, associated project, selected tools & their specific parameter overrides, target(s)/target group(s), schedule, notification settings for the scan.
    -   Ability to clone/duplicate existing scan configurations.
-   Tool Definition Management (Basic management for initially integrated tools)
-   Target Management (Define assets/targets for scans - e.g., URLs, IP addresses/ranges, code repositories).
    -   Concept of reusable 'Target Groups'.
-   Scheduling Scans (One-time, recurring daily/weekly/monthly at specific times).
    -   Clear timezone handling and display for scheduled scans.
-   Manual Scan Launch (Trigger a scan on-demand from a configuration).
-   Asynchronous Scan Execution Engine.
-   Real-time Scan Status Tracking (e.g., Queued, Running, Completed, Failed).
-   Detailed Scan History.
-   Re-scan Functionality (Re-run with current config).
-   Support for different scan triggers (Manual, Scheduled, API-driven).

## 3. Tool Integration & Management (P0)

-   Flexible Framework for integrating diverse security tools.
    -   Characteristics: plugin-based, CLI/Docker, common interface.
-   Development of Wrappers/Adaptors for a core set of initial tools (e.g., Bandit, ESLint/Prettier, Trivy/Grype, Gitleaks).
-   Ability to configure tool-specific parameters per scan configuration.
-   Standardized parsing and normalization of tool output/results into a common findings format.
    -   Includes mapping tool-specific severity levels to a standardized internal severity scale.

## 4. Findings & Vulnerability Management (P0)

-   Aggregation of findings from multiple tools for a single scan.
-   Deduplication of identical findings (Basic deduplication based on key criteria).
-   Detailed Finding View (Description, severity, evidence, tool source, timestamps, basic audit trail for status changes).
-   Comprehensive Triage Workflow (Core states: New, Confirmed, False Positive, Resolved).
-   Assigning findings to specific users for remediation.
-   Advanced filtering, sorting, and searching of findings (Basic filters: project, scan, severity, status).
-   Severity level management (Standardized internal scale based on tool mapping).

## 5. Reporting & Analytics (P0)

-   Scan-specific summary reports.
-   Exportable reports in common formats (CSV/JSON for detailed finding export).

## 6. Notifications & Alerts (Application-Level) (P0)

-   User notifications for scan completion (success/failure).
-   Alerts for newly discovered findings.
    -   Configurable severity threshold.
-   Notifications for findings assigned to a user.
-   Configurable notification preferences per user (Channels: Email as baseline MVP).

## 7. Administration & System Management (P0)

-   User Management Interface (Invite users, manage roles, activate/deactivate accounts).
    -   Admin-initiated password reset for users.
-   Configuration for global system settings (e.g., default email 'from' address, SMTP server).

## 8. User Experience (UX) & User Interface (UI) (P0 Guiding Principles)

-   Intuitive, clean, and modern web interface built with Vue.js.
-   Fast load times and responsive interactions.
-   Responsive design (desktop focus initially).
-   Clear navigation and information hierarchy.
-   Consistent UI patterns, terminology, and visual design.
-   Clear, immediate, and contextual visual feedback for user actions.
-   Workflow optimization to minimize clicks and effort for common tasks.
-   User-friendly forms and data displays with proactive validation.
-   User-friendly, informative error messages.
-   Helpful tooltips, inline help, and well-designed empty states.

## 9. Security (Platform Self-Security) (P0 Guiding Principles & Features)

-   Adherence to secure coding practices.
-   Regular automated security testing of the platform codebase (Basic SAST/SCA for its own codebase).
-   Protection against common web vulnerabilities (OWASP Top 10).
-   Robust input validation and output encoding.
-   Secure handling of secrets and credentials.
-   Ensure all API endpoints enforce appropriate authentication and fine-grained authorization checks.
-   Implement and enforce anti-CSRF tokens.
-   Dependency management and vulnerability scanning for platform components.

## 10. Documentation (P0)

-   Detailed setup guide for the local development environment.
-   Release Notes / Changelog (Essential from the very first release).

--- 