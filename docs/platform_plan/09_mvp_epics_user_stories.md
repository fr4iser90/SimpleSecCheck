# SecuLite v2: MVP Epics & User Stories Outline

**Version:** 1.0
**Date:** $(date +%Y-%m-%d)
**Source Document:** `docs/platform_plan/08_mvp_feature_list.md`

This document outlines high-level Epics and initial User Stories for the SecuLite v2 MVP features. This is a starting point for more detailed task breakdown in a project management tool.

## Epic 1: Core User Authentication & Authorization

**Goal:** Allow users to securely register, log in, manage their profiles, and ensure actions are governed by roles.
**P0 Features Covered:**
- User Authentication (Registration, Login, Logout, Password Reset)
- Password Complexity Rules & Account Lockout
- User Authorization & Role-Based Access Control (RBAC)
- User Profile Management (View/edit own profile, API key management)

**Initial User Stories:**
-   As a new user, I want to register for an account so I can access the platform.
-   As a registered user, I want to log in with my credentials so I can use the platform.
-   As a logged-in user, I want to log out securely.
-   As a user who forgot their password, I want to be able to reset it securely.
-   As an administrator, I want password complexity rules enforced to enhance security.
-   As an administrator, I want accounts to lock out after multiple failed login attempts.
-   As a logged-in user, I want to view and update my profile information (e.g., name, email).
-   As a logged-in user, I want to generate and manage API keys for programmatic access.
-   As an administrator, I want to define roles (Admin, Project Owner, Project Member, Auditor) with specific permissions.
-   As a user, I want my actions on the platform to be restricted based on my assigned role.

## Epic 2: Project & System Foundation

**Goal:** Establish core project management and system settings necessary for platform operation.
**P0 Features Covered:**
- Project Management (CRUD operations)
- Robust API Infrastructure
- Central Dashboard/Overview Page
- System Settings Management

**Initial User Stories:**
-   As a Project Owner, I want to create new projects to organize my security scans.
-   As a Project Owner/Admin, I want to view, update, and delete projects.
-   As a developer, I want a well-defined and robust API to interact with platform resources (this is an ongoing enabler for other stories).
-   As a logged-in user, I want to see a central dashboard with key metrics and recent activity upon login.
-   As an administrator, I want to configure system-wide settings like the mail server (SMTP) for notifications.

## Epic 3: Scan Setup & Configuration

**Goal:** Enable users to define, configure, and manage security scans.
**P0 Features Covered:**
- Scan Configuration Management (CRUD, clone)
- Tool Definition Management (Basic)
- Target Management (Assets & Groups)

**Initial User Stories:**
-   As a user, I want to create a new scan configuration, specifying its name, project, tools, targets, and basic schedule.
-   As a user, I want to view, update, and delete existing scan configurations.
-   As a user, I want to clone an existing scan configuration to quickly create a similar one.
-   As an administrator, I want to see a list of available security tools that can be used in scans.
-   As a user, I want to define scan targets (e.g., URLs, IP addresses, code repositories).
-   As a user, I want to create and manage reusable groups of targets.
-   As a user, I want to associate targets or target groups with my scan configurations.

## Epic 4: Scan Execution & Monitoring

**Goal:** Allow users to launch scans, monitor their progress, and view their history.
**P0 Features Covered:**
- Scheduling Scans (One-time, recurring, timezone handling)
- Manual Scan Launch
- Asynchronous Scan Execution Engine
- Real-time Scan Status Tracking
- Detailed Scan History
- Re-scan Functionality
- Support for different scan triggers (Manual, Scheduled, API)

**Initial User Stories:**
-   As a user, I want to schedule a scan to run one time at a specific date/time.
-   As a user, I want to schedule a scan to run on a recurring basis (e.g., daily, weekly).
-   As a user, I want scan schedules to correctly handle timezones.
-   As a user, I want to manually launch a configured scan on demand.
-   As a user, I want to initiate scans via an API call.
-   As a user, I want to see the real-time status of my ongoing scans (e.g., Queued, Running, Completed, Failed).
-   As a user, I want to view a detailed history of all past scans, including their status and summary.
-   As a user, I want to easily re-run a previous scan using its existing configuration.

## Epic 5: Tool Integration Backbone

**Goal:** Establish the core framework for integrating and running security tools.
**P0 Features Covered:**
- Flexible Framework for integrating diverse security tools
- Development of Wrappers/Adaptors for a core set of initial tools
- Ability to configure tool-specific parameters per scan configuration
- Standardized parsing and normalization of tool output/results

**Initial User Stories:**
-   As a platform developer, I want a framework that allows me to integrate new CLI-based or Dockerized security tools.
-   As a platform developer, I want to create wrappers/adaptors for initial tools like Bandit, ESLint, Trivy, and Gitleaks.
-   As a user configuring a scan, I want to be able to override default parameters for the selected tools.
-   As a platform developer, I want tool outputs to be parsed and normalized into a common internal format for findings.
-   As a platform developer, I want tool-specific severity levels to be mapped to a standardized internal severity scale.

## Epic 6: Findings Lifecycle Management (MVP Core)

**Goal:** Enable users to view, triage, and manage security findings identified by scans.
**P0 Features Covered:**
- Aggregation of findings from multiple tools for a single scan.
- Deduplication of identical findings (Basic).
- Detailed Finding View (Description, severity, evidence, tool source, timestamps, basic audit trail for status changes).
- Comprehensive Triage Workflow (Core states: New, Confirmed, False Positive, Resolved).
- Assigning findings to specific users for remediation.
- Advanced filtering, sorting, and searching of findings (Basic filters).
- Severity level management (Standardized internal scale).

**Initial User Stories:**
-   As a user, I want to see all findings from a scan aggregated in one place.
-   As a user, I want the system to automatically deduplicate identical findings from different tools or scans (basic).
-   As a user, I want to view detailed information for each finding, including its description, severity, evidence, and source tool.
-   As a user, I want to see when a finding was first seen and last seen, and a basic history of its status changes.
-   As a user, I want to triage findings by setting their status to New, Confirmed, False Positive, or Resolved.
-   As a Project Owner/Admin, I want to assign a finding to a specific user for remediation.
-   As a user, I want to filter and sort the list of findings based on project, scan, severity, and status.
-   As a user, I want findings to have a standardized severity level (e.g., Critical, High, Medium, Low, Info) mapped from the source tools.

## Epic 7: Basic Reporting & Export (MVP)

**Goal:** Provide users with essential reporting capabilities for scans and findings.
**P0 Features Covered:**
- Scan-specific summary reports.
- Exportable reports in common formats (CSV/JSON for detailed finding export).

**Initial User Stories:**
-   As a user, I want to view a summary report for a specific scan, showing key details and a count of findings by severity.
-   As a user, I want to export all finding details from a scan or project in CSV format for offline analysis.
-   As a user, I want to export all finding details from a scan or project in JSON format for integration with other tools.

## Epic 8: Core Notification System (MVP)

**Goal:** Inform users about important scan events and finding assignments.
**P0 Features Covered:**
- User notifications for scan completion (success/failure).
- Alerts for newly discovered findings (with configurable severity threshold).
- Notifications for findings assigned to a user.
- Configurable notification preferences per user (Channels: Email as baseline MVP).

**Initial User Stories:**
-   As a user, I want to receive an email notification when a scan I initiated completes (successfully or with failure).
-   As a user, I want to receive an email alert when a new finding above a certain severity (e.g., High, Critical) is discovered in my projects.
-   As a user, I want to be able to configure the minimum severity threshold for receiving new finding alerts.
-   As a user, I want to receive an email notification when a finding is assigned to me for remediation.
-   As a user, I want basic preferences to manage my email notifications (e.g., enable/disable certain types).

## Epic 9: System Administration Basics (MVP)

**Goal:** Provide administrators with essential tools for user and system management.
**P0 Features Covered:**
- User Management Interface (Invite users, manage roles, activate/deactivate accounts).
- Admin-initiated password reset for users.
- Configuration for global system settings (e.g., default email 'from' address, SMTP server).

**Initial User Stories:**
-   As an administrator, I want to invite new users to the platform.
-   As an administrator, I want to assign roles to users.
-   As an administrator, I want to activate or deactivate user accounts.
-   As an administrator, I want to be able to reset a user's password if they are locked out.
-   As an administrator, I want to configure the system's SMTP server settings for sending emails.
-   As an administrator, I want to set a default 'from' address for system emails.

## Epic 10: Foundational User Experience (MVP - Guiding Principles)

**Goal:** Ensure the MVP provides a usable, clear, and consistent user experience.
**P0 Features Covered:** (These are primarily guiding principles for all UI development)
- Intuitive, clean, modern web interface (Vue.js).
- Fast load times and responsive interactions.
- Responsive design (desktop focus initially).
- Clear navigation and information hierarchy.
- Consistent UI patterns, terminology, visual design.
- Clear, immediate, contextual visual feedback.
- Workflow optimization, sensible defaults.
- User-friendly forms, proactive validation.
- User-friendly, informative error messages.
- Helpful tooltips, inline help, empty states.

**Initial User Stories:** (These stories represent the *application* of the principles to MVP features)
-   As a user, I expect the interface to be easy to understand and navigate for all MVP features.
-   As a user, I expect pages and actions within the MVP scope to load quickly.
-   As a user on a desktop, I expect the MVP features to be well-laid out and functional.
-   As a user, I expect to see clear loading indicators and success/error messages for my actions within MVP features.
-   As a user, I expect forms for MVP features (e.g., project creation, scan config) to have sensible defaults and clear validation.

## Epic 11: Core Platform Security (MVP - Guiding Principles & Features)

**Goal:** Ensure the MVP is built with fundamental security practices in place.
**P0 Features Covered:** (Mix of principles and discrete features)
- Adherence to secure coding practices.
- Regular automated security testing (Basic SAST/SCA).
- Protection against common web vulnerabilities.
- Robust input validation and output encoding.
- Secure handling of secrets and credentials.
- API endpoints enforce authN/authZ.
- Anti-CSRF tokens.
- Dependency management and vulnerability scanning.

**Initial User Stories:** (Representing the implementation of these for MVP)
-   As a developer, I will follow secure coding guidelines when building MVP features.
-   As a developer, I will ensure basic SAST and SCA scans are run against the platform's codebase during MVP development.
-   As a developer, I will implement defenses against common vulnerabilities like XSS and SQLi for all MVP features handling user input.
-   As a developer, I will ensure all user-supplied input for MVP features is validated on the backend.
-   As a developer, I will ensure secrets like the Django SECRET_KEY and database credentials are not hardcoded and are handled securely for the MVP deployment.
-   As a developer, I will ensure all MVP API endpoints correctly enforce authentication and authorization rules defined in RBAC.
-   As a developer, I will ensure Django's built-in CSRF protection is active for all relevant MVP web forms.
-   As a developer, I will regularly scan project dependencies for known vulnerabilities during MVP development.

## Epic 12: Essential Developer & Release Documentation (MVP)

**Goal:** Provide the minimum necessary documentation for developers to contribute and for users to understand releases.
**P0 Features Covered:**
- Detailed setup guide for the local development environment.
- Release Notes / Changelog.

**Initial User Stories:**
-   As a new developer joining the project, I want a clear guide on how to set up my local development environment for the MVP.
-   As a user/stakeholder, I want to see release notes or a changelog for each version of the MVP that is deployed, detailing what has changed.

--- 