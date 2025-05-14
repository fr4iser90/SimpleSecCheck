# SecuLite v2 - API Design

This document specifies the design for the SecuLite v2 RESTful API. This API will serve as the interface between the Django backend and the Vue.js frontend, as well as any other potential clients.

## Table of Contents

1.  [Introduction](#1-introduction)
    *   [1.1. Purpose](#11-purpose)
    *   [1.2. RESTful Principles](#12-restful-principles)
    *   [1.3. API Versioning](#13-api-versioning)
    *   [1.4. Base URL](#14-base-url)
2.  [Authentication and Authorization](#2-authentication-and-authorization)
    *   [2.1. Authentication Mechanisms](#21-authentication-mechanisms)
    *   [2.2. Authorization and Permissions](#22-authorization-and-permissions)
3.  [Core API Resources & Endpoints](#3-core-api-resources--endpoints)
    *   [3.1. Users & UserProfiles (`/users/`, `/userprofiles/`, `/auth/`)](#31-users--userprofiles)
    *   [3.2. Organizations (`/api/v1/organizations/`)](#32-organizations)
    *   [3.3. Projects (`/api/v1/projects/`)](#33-projects)
    *   [3.4. TargetAssets (Nested under Projects: `/api/v1/projects/{project_id}/targetassets/`)](#34-targetassets)
    *   [3.5. ToolDefinitions (`/api/v1/tooldefinitions/`)](#35-tooldefinitions)
    *   [3.6. ScanConfigurations (Nested under Projects: `/api/v1/projects/{project_id}/scanconfigurations/`)](#36-scanconfigurations)
    *   [3.7. Scans (`/api/v1/scans/`)](#37-scans)
    *   [3.8. ScanToolResults (Nested under Scans: `/api/v1/scans/{scan_id}/toolresults/`)](#38-scantoolresults)
    *   [3.9. Findings (`/api/v1/findings/`)](#39-findings)
    *   [3.10. Docker Host Interaction Endpoints (`/api/v1/dockerhost/`)](#310-docker-host-interaction-endpoints)
    *   *(More resources/endpoints will be detailed here)*
4.  [Common API Conventions](#4-common-api-conventions)
    *   [4.1. Pagination](#41-pagination)
    *   [4.2. Filtering](#42-filtering)
    *   [4.3. Sorting](#43-sorting)
    *   [4.4. Error Handling](#44-error-handling)
    *   [4.5. Rate Limiting](#45-rate-limiting)
    *   [4.6. HTTP Status Codes](#46-http-status-codes)
5.  [Workflow Examples (Optional)](#5-workflow-examples-optional)

---

## 1. Introduction

### 1.1. Purpose
This API enables clients (primarily the SecuLite v2 Vue.js frontend) to interact with the platform's data and functionalities. It provides a standardized way to manage security projects, targets, scan configurations, execute scans, and retrieve results and findings.

### 1.2. RESTful Principles

The API will adhere to RESTful design principles, including:
-   Statelessness: Each request from a client will contain all the information needed by the server to understand the request.
-   Resource-Based: Interactions are based on manipulating resources identified by URLs.
-   Standard HTTP Methods: Utilizing `GET`, `POST`, `PUT`, `PATCH`, `DELETE` appropriately.
-   JSON for Data Exchange: Request and response bodies will primarily use JSON.

### 1.3. API Versioning

The API will be versioned via the URL to ensure backward compatibility as the API evolves. The initial version will be `v1`.
Example: `/api/v1/projects/`

### 1.4. Base URL

The base URL for all API endpoints will be `/api/`.
Example: `https://seculite.example.com/api/v1/...`

---

## 2. Authentication and Authorization

### 2.1. Authentication Mechanisms

-   **Token Authentication (Primary for external API clients):** Django REST Framework's `TokenAuthentication` will be used. Users can generate and use API tokens (from `UserProfile.api_key`) for programmatic access. The token will be passed in the `Authorization` HTTP header: `Authorization: Token <user_api_key>`.
-   **Session Authentication (Primary for Vue.js frontend):** For the Vue.js SPA served by Django, standard Django session authentication can be used for a more seamless user experience after login via the web interface. DRF integrates well with this.

### 2.2. Authorization and Permissions

Permissions will be handled using Django REST Framework's permission classes. Access to resources will be determined by:
-   **Authentication Status:** Most endpoints will require an authenticated user.
-   **Ownership:** Users can generally only access/modify resources they own (e.g., their `Projects`, `ScanConfigurations`).
-   **Organization Membership & Roles:** If multi-tenancy (`Organization` model) is implemented, permissions will be based on organization membership and the user's role within that organization (e.g., `OrganizationMembership.role` of 'admin' vs. 'member'). Admins of an organization might have broader access to resources within that organization.
-   Custom permission classes will be developed as needed to enforce these rules.

---

## 3. Core API Resources & Endpoints

This section will detail the specific endpoints for each resource. For each endpoint, we will specify:
-   HTTP Method & URL Path
-   Description
-   Key Request Body Parameters (for `POST`, `PUT`, `PATCH`)
-   Key Response Body Fields
-   Required Permissions

*(Detailed subsections for each resource like Users, Projects, Scans, Findings, etc., will be added here. Each will have a table or list describing its specific endpoints: LIST (GET), CREATE (POST), RETRIEVE (GET {id}), UPDATE (PUT {id}), PARTIAL_UPDATE (PATCH {id}), DELETE (DELETE {id}), and any custom actions.)*

### 3.1. Users & UserProfiles (`/users/`, `/userprofiles/`, `/auth/`)

This section details endpoints for user authentication, account management, and profile data. Many of these would typically be provided by a library like `dj_rest_auth` in conjunction with DRF.

#### 3.1.1. Authentication Endpoints (Prefix: `/api/v1/auth/`)

*   **User Registration**
    *   `POST /registration/`
    *   **Description:** Allows new users to register an account.
    *   **Request Body:** `username`, `email`, `password`, `password_confirm`. Optional: `first_name`, `last_name`.
    *   **Response Body (201 Created):** User details (`id`, `username`, `email`). If auto-login is configured, may also include `auth_token`.
    *   **Permissions:** `AllowAny` (Public).

*   **User Login (Token/Session)**
    *   `POST /login/`
    *   **Description:** Authenticates a user and provides an API token (for token-based auth) or establishes a session.
    *   **Request Body:** `username` (or `email`), `password`.
    *   **Response Body (200 OK):** `auth_token` (if token auth), user details (`id`, `username`, `email`). Session cookie set for session auth.
    *   **Permissions:** `AllowAny` (Public).

*   **User Logout**
    *   `POST /logout/`
    *   **Description:** Invalidates the user's session or current API token.
    *   **Request Body:** None.
    *   **Response Body (200 OK / 204 No Content):** Success message.
    *   **Permissions:** `IsAuthenticated`.

*   **Password Reset Request**
    *   `POST /password/reset/`
    *   **Description:** Initiates password reset; sends an email with a reset link/token.
    *   **Request Body:** `email`.
    *   **Response Body (200 OK):** Success message.
    *   **Permissions:** `AllowAny` (Public).

*   **Password Reset Confirmation**
    *   `POST /password/reset/confirm/`
    *   **Description:** Sets a new password using a valid reset token and UID.
    *   **Request Body:** `uid`, `token`, `new_password`, `new_password_confirm`.
    *   **Response Body (200 OK):** Success message.
    *   **Permissions:** `AllowAny` (Public).

*   **Password Change (for Authenticated Users)**
    *   `POST /password/change/`
    *   **Description:** Allows an authenticated user to change their current password.
    *   **Request Body:** `old_password`, `new_password`, `new_password_confirm`.
    *   **Response Body (200 OK):** Success message.
    *   **Permissions:** `IsAuthenticated`.

#### 3.1.2. Current User & Profile Endpoints (Prefix: `/api/v1/auth/`)

*   **Retrieve/Update Current User (Django `User` model)**
    *   `GET /user/`
    *   `PUT /user/`
    *   `PATCH /user/`
    *   **Description:** Get or update the basic details of the currently authenticated user.
    *   **Request Body (PUT/PATCH):** `username`, `email`, `first_name`, `last_name`.
    *   **Response Body (200 OK):** User object (`id`, `username`, `email`, `first_name`, `last_name`).
    *   **Permissions:** `IsAuthenticated`.

*   **Retrieve/Update Current UserProfile (`UserProfile` model)**
    *   `GET /userprofile/`
    *   `PUT /userprofile/`
    *   `PATCH /userprofile/`
    *   **Description:** Get or update the profile details of the currently authenticated user.
    *   **Request Body (PUT/PATCH):** `notification_preferences` (JSON), `avatar_url` (URL), `timezone` (string).
    *   **Response Body (200 OK):** UserProfile object (`user_id`, `api_key` (read-only, see dedicated endpoint), `notification_preferences`, `avatar_url`, `timezone`).
    *   **Permissions:** `IsAuthenticated`.

*   **Manage API Key for Current User**
    *   `GET /userprofile/api-key/`
        *   **Description:** Retrieve the current user's API key.
        *   **Response Body (200 OK):** `{"api_key": "<user_api_key>"}` or `{"api_key": null}`.
    *   `POST /userprofile/api-key/`
        *   **Description:** Generate/regenerate an API key for the current user. Replaces any existing key.
        *   **Response Body (200 OK / 201 Created):** `{"api_key": "<new_user_api_key>"}`.
    *   `DELETE /userprofile/api-key/`
        *   **Description:** Delete/invalidate the current user's API key.
        *   **Response Body (204 No Content):** 
    *   **Permissions (all):** `IsAuthenticated`.

#### 3.1.3. Admin User Management Endpoints (Prefix: `/api/v1/users/` & `/api/v1/userprofiles/`)

These endpoints are typically restricted to users with administrative privileges.

*   **List Users**
    *   `GET /users/`
    *   **Description:** Retrieves a paginated list of all user accounts.
    *   **Response Body (200 OK):** Paginated list of User objects.
    *   **Permissions:** `IsAdminUser`.

*   **Retrieve/Update/Delete Specific User**
    *   `GET /users/{id}/`
    *   `PUT /users/{id}/`
    *   `PATCH /users/{id}/`
    *   `DELETE /users/{id}/`
    *   **Description:** Manage a specific user account.
    *   **Request Body (PUT/PATCH):** Fields from `User` model.
    *   **Response Body (200 OK):** User object.
    *   **Permissions:** `IsAdminUser`.

*   **List UserProfiles**
    *   `GET /userprofiles/`
    *   **Description:** Retrieves a paginated list of all user profiles.
    *   **Response Body (200 OK):** Paginated list of UserProfile objects.
    *   **Permissions:** `IsAdminUser`.

*   **Retrieve/Update/Delete Specific UserProfile**
    *   `GET /userprofiles/{user_id}/` (Note: `{user_id}` as UserProfile has a OneToOneField to User as PK)
    *   `PUT /userprofiles/{user_id}/`
    *   `PATCH /userprofiles/{user_id}/`
    *   `DELETE /userprofiles/{user_id}/`
    *   **Description:** Manage a specific user profile.
    *   **Request Body (PUT/PATCH):** Fields from `UserProfile` model.
    *   **Response Body (200 OK):** UserProfile object.
    *   **Permissions:** `IsAdminUser`.

### 3.2. Organizations (`/api/v1/organizations/`)

Endpoints for managing organizations and their members. Assumes multi-tenancy is implemented.

#### 3.2.1. Organization Management

*   **List Organizations**
    *   `GET /api/v1/organizations/`
    *   **Description:** Retrieves organizations. Behavior may vary: all orgs for superusers, orgs the user is a member of for others.
    *   **Query Params:** `?is_member=true` (current user is member), `?is_owner=true` (current user is owner).
    *   **Response Body (200 OK):** Paginated list of Organization objects (`id`, `name`, `owner`, `member_count`, `created_at`).
    *   **Permissions:** `IsAuthenticated`.

*   **Create Organization**
    *   `POST /api/v1/organizations/`
    *   **Description:** Creates a new organization. The creating user becomes the owner.
    *   **Request Body:** `name` (string, required), `description` (string, optional).
    *   **Response Body (201 Created):** Organization object.
    *   **Permissions:** `IsAuthenticated` (specific permission like `CanCreateOrganization` might be added).

*   **Retrieve Organization**
    *   `GET /api/v1/organizations/{org_id}/`
    *   **Description:** Retrieves details of a specific organization.
    *   **Response Body (200 OK):** Organization object (including details like members if requested via query param or serializer depth).
    *   **Permissions:** `IsOrganizationMemberOrAdmin` (custom: user is member or admin of this org) or `IsSuperuser`.

*   **Update Organization**
    *   `PUT /api/v1/organizations/{org_id}/`
    *   `PATCH /api/v1/organizations/{org_id}/`
    *   **Description:** Updates an organization's details.
    *   **Request Body:** `name` (string), `description` (string), `owner_id` (user ID, restricted access).
    *   **Response Body (200 OK):** Updated Organization object.
    *   **Permissions:** `IsOrganizationAdmin` (custom: user is admin of this org) or `IsOrganizationOwner` or `IsSuperuser`.

*   **Delete Organization**
    *   `DELETE /api/v1/organizations/{org_id}/`
    *   **Description:** Deletes an organization (soft delete by setting `is_active=False` might be preferred).
    *   **Response Body (204 No Content):** 
    *   **Permissions:** `IsOrganizationOwner` or `IsSuperuser`.

#### 3.2.2. Organization Member Management (Prefix: `/api/v1/organizations/{org_id}/members/`)

*   **List Organization Members**
    *   `GET /`
    *   **Description:** Lists members of a specific organization, including their roles.
    *   **Response Body (200 OK):** Paginated list of `OrganizationMembership` objects (or serialized User objects with role: `user_id`, `username`, `email`, `role`).
    *   **Permissions:** `IsOrganizationMemberOrAdmin`.

*   **Add Member to Organization**
    *   `POST /`
    *   **Description:** Adds an existing user to the organization with a specified role.
    *   **Request Body:** `user_id` (ID of the user to add), `role` (string, e.g., 'member', 'admin', from `ORGANIZATION_ROLE_CHOICES`).
    *   **Response Body (201 Created):** `OrganizationMembership` object.
    *   **Permissions:** `IsOrganizationAdmin`.

*   **Retrieve Organization Member Details**
    *   `GET /{membership_id}/` (or potentially `/{user_id}/` if using user ID as lookup and handling uniqueness)
    *   **Description:** Retrieves details of a specific membership record (user's role in the org).
    *   **Response Body (200 OK):** `OrganizationMembership` object.
    *   **Permissions:** `IsOrganizationMemberOrAdmin`.

*   **Update Organization Member's Role**
    *   `PUT /{membership_id}/` (or `PATCH`)
    *   **Description:** Updates a member's role within the organization.
    *   **Request Body:** `role` (string).
    *   **Response Body (200 OK):** Updated `OrganizationMembership` object.
    *   **Permissions:** `IsOrganizationAdmin`.

*   **Remove Member from Organization**
    *   `DELETE /{membership_id}/`
    *   **Description:** Removes a user from an organization.
    *   **Response Body (204 No Content):** 
    *   **Permissions:** `IsOrganizationAdmin` (for removing others) or `IsAuthenticated` (for a user to leave their own membership, potentially via a different endpoint like `/api/v1/organizations/{org_id}/leave/`).

### 3.3. Projects (`/api/v1/projects/`)

Endpoints for managing projects. Projects can be owned by an individual user or an organization.

*   **List Projects**
    *   `GET /api/v1/projects/`
    *   **Description:** Retrieves projects accessible to the current user (owned individually or through organization membership).
    *   **Query Params:** `organization_id` (filter by specific organization), `owner_user_id` (filter by specific user owner), `name` (search by name), `is_active` (boolean).
    *   **Response Body (200 OK):** Paginated list of Project objects (`id`, `name`, `description`, `owner_user`, `owner_organization`, `is_active`, `created_at`, `updated_at`).
    *   **Permissions:** `IsAuthenticated`.

*   **Create Project**
    *   `POST /api/v1/projects/`
    *   **Description:** Creates a new project. If `owner_organization_id` is provided, the user must have rights to create projects for that org. Otherwise, it's owned by the current user.
    *   **Request Body:** `name` (string, required), `description` (string, optional), `owner_organization_id` (ID, optional), `owner_user_id` (ID, optional - usually defaults to current user if `owner_organization_id` is null. Backend logic validates one owner type).
    *   **Response Body (201 Created):** Project object.
    *   **Permissions:** `IsAuthenticated`. (Custom permission like `CanCreateProjectInOrganization` if `owner_organization_id` is passed).

*   **Retrieve Project**
    *   `GET /api/v1/projects/{project_id}/`
    *   **Description:** Retrieves details of a specific project.
    *   **Query Params:** `include_assets=true`, `include_scan_configs=true` (to optionally embed related objects).
    *   **Response Body (200 OK):** Project object.
    *   **Permissions:** `IsProjectOwnerOrMember` (custom: user owns the project directly, or is a member of the owning organization) or `IsSuperuser`.

*   **Update Project**
    *   `PUT /api/v1/projects/{project_id}/`
    *   `PATCH /api/v1/projects/{project_id}/`
    *   **Description:** Updates a project's details. Changing ownership might be restricted.
    *   **Request Body:** `name`, `description`, `is_active`. (Ownership fields `owner_user_id`, `owner_organization_id` updateable with stricter permissions).
    *   **Response Body (200 OK):** Updated Project object.
    *   **Permissions:** `IsProjectOwnerOrAdmin` (custom: user owns project directly, or is admin in owning org) or `IsSuperuser`.

*   **Delete Project**
    *   `DELETE /api/v1/projects/{project_id}/`
    *   **Description:** Deletes a project (soft delete by setting `is_active=False` is recommended).
    *   **Response Body (204 No Content):** 
    *   **Permissions:** `IsProjectOwnerOrAdmin` or `IsSuperuser`.

### 3.4. TargetAssets (Nested under Projects: `/api/v1/projects/{project_id}/targetassets/`)

Endpoints for managing specific scannable assets within a project.

*   **List TargetAssets for a Project**
    *   `GET /api/v1/projects/{project_id}/targetassets/`
    *   **Description:** Retrieves target assets for a specific project.
    *   **Query Params:** `asset_type` (e.g., 'url', 'git_repository'), `name` (search by name), `is_active` (boolean).
    *   **Response Body (200 OK):** Paginated list of TargetAsset objects (`id`, `project_id`, `name`, `asset_type`, `identifier`, `metadata`, `description`, `is_active`, `created_at`, `updated_at`).
    *   **Permissions:** `IsProjectOwnerOrMember` (user has access to the parent project).

*   **Create TargetAsset for a Project**
    *   `POST /api/v1/projects/{project_id}/targetassets/`
    *   **Description:** Adds a new target asset to the specified project.
    *   **Request Body:** `name` (string, optional), `asset_type` (string, required from `ASSET_TYPE_CHOICES`), `identifier` (string, required, e.g., URL, git path), `metadata` (JSON, optional), `description` (string, optional).
    *   **Response Body (201 Created):** TargetAsset object.
    *   **Permissions:** `IsProjectOwnerOrAdmin` (user has admin rights on the parent project).

*   **Retrieve Specific TargetAsset**
    *   `GET /api/v1/projects/{project_id}/targetassets/{asset_id}/`
    *   **Description:** Retrieves details of a specific target asset.
    *   **Response Body (200 OK):** TargetAsset object.
    *   **Permissions:** `IsProjectOwnerOrMember`.

*   **Update Specific TargetAsset**
    *   `PUT /api/v1/projects/{project_id}/targetassets/{asset_id}/`
    *   `PATCH /api/v1/projects/{project_id}/targetassets/{asset_id}/`
    *   **Description:** Updates details of a specific target asset.
    *   **Request Body:** `name`, `asset_type`, `identifier`, `metadata`, `description`, `is_active`.
    *   **Response Body (200 OK):** Updated TargetAsset object.
    *   **Permissions:** `IsProjectOwnerOrAdmin`.

*   **Delete Specific TargetAsset**
    *   `DELETE /api/v1/projects/{project_id}/targetassets/{asset_id}/`
    *   **Description:** Deletes a specific target asset from the project.
    *   **Response Body (204 No Content):** 
    *   **Permissions:** `IsProjectOwnerOrAdmin`.

### 3.5. ToolDefinitions (`/api/v1/tooldefinitions/`)

Endpoints for retrieving information about available security tool definitions. Management of these definitions is typically an administrative task.

*   **List ToolDefinitions**
    *   `GET /api/v1/tooldefinitions/`
    *   **Description:** Retrieves a list of all available and active tool definitions.
    *   **Query Params:** `tool_type` (e.g., 'dast', 'sast'), `name` (search by name), `target_asset_type` (e.g., 'url', to find tools compatible with a given asset type).
    *   **Response Body (200 OK):** Paginated list of ToolDefinition objects (`id`, `tool_id`, `name`, `description`, `tool_type`, `target_asset_types`, `version`, `default_config_template`, `is_active`).
    *   **Permissions:** `IsAuthenticated` (all authenticated users can view available tools).

*   **Retrieve ToolDefinition**
    *   `GET /api/v1/tooldefinitions/{id_or_tool_id}/` (Can use either primary key `id` or the unique `tool_id`)
    *   **Description:** Retrieves details of a specific tool definition.
    *   **Response Body (200 OK):** ToolDefinition object.
    *   **Permissions:** `IsAuthenticated`.

#### 3.5.1. Admin Management of ToolDefinitions (Admin-only)

These endpoints are restricted to users with `IsAdminUser` permission.

*   **Create ToolDefinition**
    *   `POST /api/v1/tooldefinitions/`
    *   **Description:** Creates a new tool definition.
    *   **Request Body:** All fields for `ToolDefinition` model (e.g., `tool_id`, `name`, `description`, `tool_type`, `target_asset_types`, `version`, `docker_image_name`, `entrypoint_command`, `default_config_template`, `result_parser_info`, `is_active`).
    *   **Response Body (201 Created):** ToolDefinition object.
    *   **Permissions:** `IsAdminUser`.

*   **Update ToolDefinition**
    *   `PUT /api/v1/tooldefinitions/{id_or_tool_id}/`
    *   `PATCH /api/v1/tooldefinitions/{id_or_tool_id}/`
    *   **Description:** Updates an existing tool definition.
    *   **Request Body:** Fields from `ToolDefinition` model.
    *   **Response Body (200 OK):** Updated ToolDefinition object.
    *   **Permissions:** `IsAdminUser`.

*   **Delete ToolDefinition**
    *   `DELETE /api/v1/tooldefinitions/{id_or_tool_id}/`
    *   **Description:** Deletes a tool definition. Soft delete (`is_active=False`) is preferred if results are linked via `on_delete=models.PROTECT`.
    *   **Response Body (204 No Content):** 
    *   **Permissions:** `IsAdminUser`.

### 3.6. ScanConfigurations (Nested under Projects: `/api/v1/projects/{project_id}/scanconfigurations/`)

Endpoints for managing scan configurations within a specific project.

*   **List ScanConfigurations for a Project**
    *   `GET /api/v1/projects/{project_id}/scanconfigurations/`
    *   **Description:** Retrieves all scan configurations associated with the given project.
    *   **Query Params:** `name` (search by name), `is_active` (boolean), `schedule_type`.
    *   **Response Body (200 OK):** Paginated list of ScanConfiguration objects (`id`, `project_id`, `name`, `description`, `target_assets` (IDs or brief details), `tools_and_configs`, `schedule_type`, `schedule`, `is_active`, `created_at`, `updated_at`, `last_triggered_at`).
    *   **Permissions:** `IsProjectOwnerOrMember`.

*   **Create ScanConfiguration for a Project**
    *   `POST /api/v1/projects/{project_id}/scanconfigurations/`
    *   **Description:** Creates a new scan configuration for the specified project.
    *   **Request Body:** `name` (string, required), `description` (string, optional), `target_assets` (list of `TargetAsset` IDs, optional), `tools_and_configs` (JSON array, required, e.g., `[{"tool_id": "semgrep_sast", "overrides": {"ruleset": "custom.yml"}}]`), `schedule_type` (string, from `SCHEDULE_TYPE_CHOICES`), `schedule` (string, optional, e.g., cron expression), `is_active` (boolean, optional, default: true).
    *   **Response Body (201 Created):** ScanConfiguration object.
    *   **Permissions:** `IsProjectOwnerOrAdmin`.

*   **Retrieve Specific ScanConfiguration**
    *   `GET /api/v1/projects/{project_id}/scanconfigurations/{config_id}/`
    *   **Description:** Retrieves details of a specific scan configuration.
    *   **Response Body (200 OK):** ScanConfiguration object.
    *   **Permissions:** `IsProjectOwnerOrMember`.

*   **Update Specific ScanConfiguration**
    *   `PUT /api/v1/projects/{project_id}/scanconfigurations/{config_id}/`
    *   `PATCH /api/v1/projects/{project_id}/scanconfigurations/{config_id}/`
    *   **Description:** Updates an existing scan configuration.
    *   **Request Body:** Fields from `ScanConfiguration` model (e.g., `name`, `description`, `target_assets`, `tools_and_configs`, `schedule_type`, `schedule`, `is_active`).
    *   **Response Body (200 OK):** Updated ScanConfiguration object.
    *   **Permissions:** `IsProjectOwnerOrAdmin`.

*   **Delete Specific ScanConfiguration**
    *   `DELETE /api/v1/projects/{project_id}/scanconfigurations/{config_id}/`
    *   **Description:** Deletes a scan configuration.
    *   **Response Body (204 No Content):** 
    *   **Permissions:** `IsProjectOwnerOrAdmin`.

*   **Launch Scan from Configuration (Custom Action)**
    *   `POST /api/v1/projects/{project_id}/scanconfigurations/{config_id}/launch_scan/`
    *   **Description:** Manually triggers a new scan based on this configuration.
    *   **Request Body (optional):** `{"trigger_notes": "Manual launch for pre-release testing"}` or potential minor runtime overrides if supported.
    *   **Response Body (202 Accepted):** Newly created `Scan` object (or its ID and status) indicating the scan has been initiated.
    *   **Permissions:** `IsProjectOwnerOrAdmin` (or a more specific `CanLaunchScansInProject` permission).

### 3.7. Scans (`/api/v1/scans/`)

Endpoints for viewing scan executions and managing their lifecycle (e.g., cancelling). Creating scans is primarily handled via the `launch_scan` action on a `ScanConfiguration`.

*   **List Scans**
    *   `GET /api/v1/scans/`
    *   **Description:** Retrieves a list of scans. Admins can see all scans; regular users see scans for projects they have access to.
    *   **Query Params:** `project_id`, `scan_configuration_id`, `status` (e.g., 'running', 'completed', 'failed'), `trigger_type`, `triggered_by_user_id`, `start_time__gte` (ISO datetime), `start_time__lte` (ISO datetime), `ordering` (e.g., '-start_time').
    *   **Response Body (200 OK):** Paginated list of Scan objects (`id`, `project_id`, `scan_configuration_id`, `status`, `trigger_type`, `start_time`, `end_time`, `summary_data`).
    *   **Permissions:** `IsAuthenticated`. (Filtering by project access is applied for non-admins).

*   **Retrieve Scan Details**
    *   `GET /api/v1/scans/{scan_id}/`
    *   **Description:** Retrieves detailed information about a specific scan, including its status, summary, and potentially links or embedded tool results.
    *   **Query Params:** `include_tool_results=true` (to embed tool results), `include_findings_summary=true` (to embed a summary of findings by severity).
    *   **Response Body (200 OK):** Scan object (potentially with nested `ScanToolResult` objects or an aggregated findings summary based on query params).
    *   **Permissions:** `HasAccessToScanProject` (custom: user has access to the project associated with this scan).

*   **Cancel a Running Scan (Custom Action)**
    *   `POST /api/v1/scans/{scan_id}/cancel/`
    *   **Description:** Attempts to request cancellation of an ongoing scan (status might move to 'cancelling' then 'cancelled').
    *   **Request Body:** None.
    *   **Response Body (200 OK / 202 Accepted):** Success message or updated Scan object showing the new status.
    *   **Permissions:** `IsProjectOwnerOrAdmin` (for the scan's project) or `IsScanTriggerUser` (if the user who triggered it should be allowed to cancel, might need time limits).

*   **Re-Scan (based on a previous scan's configuration - Custom Action)**
    *   `POST /api/v1/scans/{scan_id}/rescan/`
    *   **Description:** Creates and launches a new scan using the same `ScanConfiguration` as the specified scan. Useful for re-running failed or completed scans.
    *   **Request Body (optional):** `{"trigger_notes": "Rescan of scan ID {scan_id}"}`.
    *   **Response Body (202 Accepted):** Newly created `Scan` object (or its ID and status) indicating the new scan has been initiated.
    *   **Permissions:** `IsProjectOwnerOrAdmin` (for the scan's project).

### 3.8. ScanToolResults (Nested under Scans: `/api/v1/scans/{scan_id}/toolresults/`)

Endpoints for viewing the results of individual tools run as part of a scan. These are typically read-only for API clients as they are generated by the backend scan processes.

*   **List Tool Results for a Scan**
    *   `GET /api/v1/scans/{scan_id}/toolresults/`
    *   **Description:** Retrieves all tool results associated with a specific scan.
    *   **Query Params:** `tool_definition_id` (filter by a specific tool), `status` (e.g., 'completed', 'failed', 'no_findings').
    *   **Response Body (200 OK):** Paginated list of ScanToolResult objects (`id`, `scan_id`, `tool_definition` (ID or brief details), `status`, `start_time`, `end_time`, `summary`, `error_message`, `findings_count` (calculated or from summary)).
    *   **Permissions:** `HasAccessToScanProject` (user has access to the parent scan's project).

*   **Retrieve Specific Tool Result**
    *   `GET /api/v1/scans/{scan_id}/toolresults/{toolresult_id}/`
    *   **Description:** Retrieves details of a specific tool's result within a scan.
    *   **Query Params:** `include_findings=true` (to embed/link findings from this tool result; pagination for findings might be needed here or use a separate findings endpoint filtered by `toolresult_id`).
    *   **Response Body (200 OK):** ScanToolResult object (potentially with nested/linked `Finding` objects or a summary of findings).
    *   **Permissions:** `HasAccessToScanProject`.

*(Note: Create, Update, Delete operations for ScanToolResults are generally not exposed via the API as these records are direct outputs of the backend scan execution engine.)*

### 3.9. Findings (`/api/v1/findings/`)

Endpoints for viewing, triaging, and managing security findings.

*   **List Findings**
    *   `GET /api/v1/findings/`
    *   **Description:** Retrieves a list of findings. Access is governed by project ownership/membership associated with the findings.
    *   **Query Params:** `project_id`, `scan_id`, `scan_tool_result_id`, `status` (e.g., 'new', 'confirmed'), `severity` (e.g., 'critical', 'high'), `cve_id`, `cwe_id`, `fingerprint`, `is_false_positive` (boolean), `is_ignored` (boolean), `assigned_to_user_id`, `tags__contains` (e.g., 'pci', 'gdpr'), `search` (for full-text search on title, description, location), `ordering` (e.g., '-severity', 'created_at').
    *   **Response Body (200 OK):** Paginated list of Finding objects (key fields like `id`, `project_id`, `title`, `severity`, `status`, `cve_id`, `cwe_id`, `first_seen_at_scan_id`, `last_seen_at_scan_id`, `assigned_to_user_id`).
    *   **Permissions:** `IsAuthenticated`. (Backend applies filtering based on user's project access).

*   **Retrieve Finding Details**
    *   `GET /api/v1/findings/{finding_id}/`
    *   **Description:** Retrieves detailed information about a specific finding.
    *   **Query Params:** `include_scan_info=true`, `include_project_info=true`, `include_tool_result_info=true`.
    *   **Response Body (200 OK):** Full Finding object, potentially with expanded related objects based on query params.
    *   **Permissions:** `HasAccessToFindingProject` (custom: user has access to the project this finding belongs to).

*   **Update Finding (Triage/Management)**
    *   `PATCH /api/v1/findings/{finding_id}/` (Using PATCH for partial updates is generally preferred for triage actions)
    *   **Description:** Updates attributes of a finding, primarily for triage, assignment, and status management.
    *   **Request Body:** `status` (from `FINDING_STATUS_CHOICES`), `severity` (string, if override is allowed, e.g., by admin/lead), `is_false_positive` (boolean), `is_ignored` (boolean), `resolution_notes` (text), `assigned_to_user_id` (ID of a user), `due_date` (date), `tags` (list of strings).
    *   **Response Body (200 OK):** Updated Finding object.
    *   **Permissions:** `CanManageFindingsInProject` (custom: user has triage/management rights on the finding's project).

*   **Bulk Update Findings (Status/Assignment)**
    *   `POST /api/v1/findings/bulk_update/` (or `PATCH`)
    *   **Description:** Allows updating common attributes (like status or assignee) for multiple findings at once.
    *   **Request Body:** Example: `{"finding_ids": [101, 102, 105], "updates": {"status": "confirmed", "assigned_to_user_id": 5, "resolution_notes": "Reviewed batch."}}`.
        *   The `updates` object would contain fields and values to apply to all specified `finding_ids`.
    *   **Response Body (200 OK):** Summary of the update (e.g., `{"updated_count": 3, "failed_ids": []}`) or a list of updated Finding objects (potentially too large, summary preferred).
    *   **Permissions:** `CanManageFindingsInProject`.

*(Note: Direct creation or deletion of Findings via the API is typically not allowed. Findings are generated by scan processes. Status changes like 'false_positive' or 'resolved' combined with data retention policies handle their lifecycle.)*

#### 3.9.1. Finding Comments/Audit Log (Future Consideration)
*   `GET /api/v1/findings/{finding_id}/comments/`
*   `POST /api/v1/findings/{finding_id}/comments/`
    *   **Description:** To manage comments or an audit trail for a finding. This would likely involve a separate `FindingComment` model.
    *   **Permissions:** `HasAccessToFindingProject` for GET, `CanManageFindingsInProject` for POST.

### 3.10. Docker Host Interaction Endpoints (`/api/v1/dockerhost/`)

These endpoints enable the SecuLite backend (with appropriate permissions and configuration for Docker socket access) to retrieve information about Docker containers running locally on the host. This primarily serves the feature of selecting codebases from Docker volumes as scan targets.

**Prerequisites:**
- The SecuLite backend must be configured to access the host's Docker socket (see `05_docker_setup.md`).
- The calling user requires appropriate permissions (e.g., `IsAdminUser` or a more specific permission like `CanAccessDockerHostInfo`).

#### 3.10.1. List Running Docker Containers

*   `GET /api/v1/dockerhost/containers/`
    *   **Description:** Retrieves a list of Docker containers currently running on the host. The information returned should be relevant for identification and selection in the frontend.
    *   **Query Params:**
        *   `name_filter` (string, optional): Filters containers whose names contain the specified string.
        *   `status_filter` (string, optional, default: 'running'): Filters by container status (e.g., 'running', 'exited').
    *   **Response Body (200 OK):** Paginated list of Container Information objects.
        ```json
        {
          "count": 1,
          "next": null,
          "previous": null,
          "results": [
            {
              "id": "abcdef123456", // Docker Container ID (short or long)
              "name": "my_application_container_1",
              "image": "my_app_image:latest",
              "status": "running", // e.g., 'running', 'exited', 'paused'
              "created_at": "2023-10-26T10:00:00Z", // Container creation time
              "ports": [ // Optional: exposed ports for additional info
                { "host_port": 8080, "container_port": 80, "protocol": "tcp" }
              ]
            }
            // ... other containers
          ]
        }
        ```
    *   **Permissions:** `IsAdminUser` (or a more specific permission `CanAccessDockerHostInfo`).

#### 3.10.2. Retrieve Potential Code Paths from a Container

*   `GET /api/v1/dockerhost/containers/{container_id}/code-paths/`
    *   **Description:** For a specific Docker container, retrieves a list of host filesystem paths derived from its volume mounts that could potentially contain codebases. The backend analyzes the container's volume mounts and returns the corresponding host paths.
    *   **Path Parameter:**
        *   `container_id` (string, required): The ID of the Docker container.
    *   **Response Body (200 OK):**
        ```json
        {
          "container_id": "abcdef123456",
          "container_name": "my_application_container_1",
          "potential_code_paths": [
            {
              "host_path": "/path/on/host/to/volume_for_html",
              "path_in_container": "/var/www/html",
              "volume_type": "bind", // 'bind' or 'volume'
              "description": "Potential codebase (e.g., web server root)" // Optional description
            },
            {
              "host_path": "/another/path/on/host/to/app_code",
              "path_in_container": "/app/src",
              "volume_type": "bind",
              "description": "Potential codebase (e.g., application sources)"
            }
            // ... other relevant paths
          ]
        }
        ```
        If no relevant paths are found or the container has no volumes, `potential_code_paths` will be an empty array.
    *   **Permissions:** `IsAdminUser` (or `CanAccessDockerHostInfo`).

---

## 4. Common API Conventions

### 4.1. Pagination
List endpoints that can return a large number of items will be paginated using DRF's pagination classes (e.g., `PageNumberPagination` or `LimitOffsetPagination`). Responses will include links to next/previous pages and total counts.
Example query: `GET /api/v1/findings/?page=2&page_size=20`

### 4.2. Filtering
DRF's filtering backends (e.g., `django-filter`) will be used to allow filtering on list endpoints based on field values.
Example query: `GET /api/v1/findings/?status=new&severity=critical`

### 4.3. Sorting
List endpoints will support sorting based on specified fields.
Example query: `GET /api/v1/findings/?ordering=-created_at` (sort by creation date, descending)

### 4.4. Error Handling
A standardized JSON error response format will be used:
```json
{
  "detail": "Error message or description.",
  "errors": { // Optional: field-specific errors for validation issues
    "field_name": ["Error message for this field."]
  },
  "error_code": "UNIQUE_ERROR_CODE" // Optional: specific error code for client handling
}
```

### 4.5. Rate Limiting
Rate limiting will be implemented using DRF's throttling policies to prevent abuse and ensure fair usage, especially for unauthenticated or per-user authenticated endpoints.

### 4.6. HTTP Status Codes
Standard HTTP status codes will be used to indicate the success or failure of API requests (e.g., 200 OK, 201 Created, 204 No Content, 400 Bad Request, 401 Unauthorized, 403 Forbidden, 404 Not Found, 500 Internal Server Error).

---

## 5. Workflow Examples (Optional)

*(This section can later be populated with sequences of API calls for common operations, e.g., "Onboarding a new project and launching an initial scan".)*

--- 