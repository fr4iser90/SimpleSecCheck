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

(Further Epics for Findings Management, Reporting, Notifications, Admin, UX, Security, and Documentation to be detailed based on P0 features...)

--- 