# SecuLite v2 - Data Model and Database Schema

This document outlines the core data models and database schema for SecuLite v2. It serves as the blueprint for the Django models that will represent the platform's entities and their relationships.

## Table of Contents

1.  [Introduction](#1-introduction)
2.  [Core Entities & Django Models](#2-core-entities--django-models)
    *   [2.1. `UserProfile`](#21-userprofile)
    *   [2.2. `Organization`](#22-organization-optional-for-multi-tenancy)
    *   [2.3. `Project`](#23-project-replaces-scantarget)
    *   [2.4. `TargetAsset`](#24-targetasset)
    *   [2.5. `ScanConfiguration`](#25-scanconfiguration)
    *   [2.6. `Scan`](#26-scan)
    *   [2.7. `ScanToolResult`](#27-scantoolresult)
    *   [2.8. `Finding`](#28-finding)
    *   [2.9. `ToolDefinition`](#29-tooldefinition)
3.  [Relationships Between Models (Conceptual ERD)](#3-relationships-between-models-conceptual-erd)
4.  [Key Fields and Data Types (Detailed per Model)](#4-key-fields-and-data-types-detailed-per-model)
    *   [4.1. `UserProfile`](#41-userprofile)
    *   [4.2. `Organization`](#42-organization)
    *   [4.2.1. `OrganizationMembership` (Through Model)](#421-organizationmembership-through-model)
    *   [4.3. `Project`](#43-project)
    *   [4.4. `TargetAsset`](#44-targetasset)
    *   [4.5. `ToolDefinition`](#45-tooldefinition)
    *   [4.6. `ScanConfiguration`](#46-scanconfiguration)
    *   [4.7. `Scan`](#47-scan)
    *   [4.8. `ScanToolResult`](#48-scantoolresult)
    *   [4.9. `Finding`](#49-finding)
5.  [Database Schema Considerations](#5-database-schema-considerations)

---

## 1. Introduction

The data model is a critical foundation for SecuLite v2. It defines how information about users, scan targets, scan processes, results, and findings is structured and stored. A well-designed data model ensures data integrity, facilitates efficient querying, and supports the platform's features and scalability. We will use Django's Object-Relational Mapper (ORM) to implement these models, leveraging PostgreSQL as the database system.

---

## 2. Core Entities & Django Models

Below are the primary entities that will be represented as Django models. Some names have been refined for clarity (e.g., `Project` instead of `ScanTarget`, `TargetAsset` for specific assets within a project).

### 2.1. `UserProfile` (Extends Django's `User`)

*   **Purpose:** Stores additional information related to a user beyond Django's built-in `User` model (username, email, password, first_name, last_name).
*   **Key Attributes (to be detailed in section 4):** API keys, notification preferences, role within an organization (if multi-tenancy is implemented).

### 2.2. `Organization` (Optional, for multi-tenancy)

*   **Purpose:** Groups users and projects. Useful if SecuLite v2 is to be used by multiple distinct teams or clients.
*   **Status:** To be decided if this is a v2.0 core feature or later enhancement.
*   **Key Attributes:** Name, owner, members (ManyToManyField to `UserProfile`).

### 2.3. `Project` (Replaces `ScanTarget` for better semantics)

*   **Purpose:** Represents a high-level entity that users want to secure and monitor. A project can contain multiple specific assets to be scanned (e.g., a web application project might have a URL, a source code repository, and associated container images).
*   **Key Attributes:** Name, description, owner (`UserProfile` or `Organization`), creation date, last updated date.

### 2.4. `TargetAsset`

*   **Purpose:** Defines a specific asset within a `Project` that can be scanned. This allows a project to group different types of scannable items.
*   **Key Attributes:** Associated `Project` (ForeignKey), asset type (e.g., 'URL', 'GIT_REPOSITORY', 'DOCKER_IMAGE', 'FILE_UPLOAD'), asset identifier (e.g., the actual URL, repo path, image name), metadata (JSONField for type-specific details like branch for git, specific paths to scan).

### 2.5. `ScanConfiguration`

*   **Purpose:** Defines how a `Project` or a specific `TargetAsset` should be scanned. This includes which tools to run, their specific configurations, and scheduling parameters.
*   **Key Attributes:** Associated `Project` or `TargetAsset`, name (e.g., "Daily Web Scan", "CI SAST Check"), tools to run (ManyToManyField to `ToolDefinition`), tool-specific configurations (JSONField), schedule (e.g., cron expression for periodic scans), enabled/disabled status.

### 2.6. `Scan`

*   **Purpose:** Represents a single execution instance of a `ScanConfiguration` against the defined `TargetAsset`(s) within a `Project`.
*   **Key Attributes:** Associated `ScanConfiguration`, triggered by (`UserProfile` or 'scheduled'), start time, end time, status (e.g., 'PENDING', 'RUNNING', 'COMPLETED', 'FAILED', 'CANCELLED'), overall progress (percentage or steps).

### 2.7. `ScanToolResult`

*   **Purpose:** Stores the summary and raw output from a specific security tool run as part of a `Scan`.
*   **Key Attributes:** Associated `Scan` (ForeignKey), `ToolDefinition` (ForeignKey indicating which tool), status for this tool (e.g., 'SUCCESS', 'ERROR'), start time, end time, summary (JSONField or TextField), raw output file path (or reference if stored elsewhere), number of findings from this tool.

### 2.8. `Finding`

*   **Purpose:** Represents a specific vulnerability or issue identified by a tool in a `ScanToolResult`.
*   **Key Attributes:** Associated `ScanToolResult` (ForeignKey), title/name, description, severity (e.g., 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'INFORMATIONAL'), CVE ID (if applicable), CWE ID (if applicable), location (e.g., file path, URL, line number), evidence/snippet, status (e.g., 'NEW', 'CONFIRMED', 'FALSE_POSITIVE', 'RESOLVED', 'IGNORED'), resolution notes, first seen timestamp, last seen timestamp, unique identifier (to track across scans).

### 2.9. `ToolDefinition`

*   **Purpose:** Defines a security tool that SecuLite v2 can integrate with and orchestrate.
*   **Key Attributes:** Name (e.g., 'ZAP Baseline', 'Semgrep', 'Trivy Image'), type (e.g., 'DAST', 'SAST', 'SCA', 'IMAGE_SCANNER'), description, command/API integration details (JSONField), default configuration template (JSONField).

---

## 3. Relationships Between Models (Conceptual ERD)

*(This section will visually (or textually) describe the relationships, e.g., One-to-Many, Many-to-Many. For example:)*
*   `UserProfile` (1) -- (0..N) `Project` (Owner)
*   `Project` (1) -- (1..N) `TargetAsset`
*   `Project` (1) -- (0..N) `ScanConfiguration`
*   `ScanConfiguration` (1) -- (0..N) `Scan`
*   `ScanConfiguration` (M) -- (N) `ToolDefinition` (Tools to run)
*   `Scan` (1) -- (1..N) `ScanToolResult`
*   `ScanToolResult` (1) -- (0..N) `Finding`
*   `ScanToolResult` (1) -- (1) `ToolDefinition`
*   *(If `Organization` is used, it would have relationships with `UserProfile` and `Project`)*

---

## 4. Key Fields and Data Types (Detailed per Model)

*(This section will be populated with detailed field definitions for each model listed in section 2, including Django field types like `CharField`, `TextField`, `IntegerField`, `DateTimeField`, `BooleanField`, `JSONField`, `ForeignKey`, `ManyToManyField`, etc. This will be a significant part of the document.)*

### 4.1. `UserProfile`

*   **`user`**: `OneToOneField(User, on_delete=models.CASCADE, primary_key=True)`
    *   Description: Links to Django's built-in `User` model (which handles `username`, `email`, `password`, `first_name`, `last_name`). `primary_key=True` makes the `User`'s ID the primary key for `UserProfile` as well.
*   **`api_key`**: `CharField(max_length=64, unique=True, blank=True, null=True, help_text="API key for programmatic access")`
    *   Description: Auto-generated, unique API key for the user.
*   **`notification_preferences`**: `JSONField(default=dict, blank=True, help_text="User's notification settings, e.g., {\"scan_completed_email\": true}")`
    *   Description: Stores preferences for various types of notifications.
*   **`avatar_url`**: `URLField(max_length=255, blank=True, null=True, help_text="Optional URL to user's avatar image")`
    *   Description: Link to an external avatar image.
*   **`timezone`**: `CharField(max_length=64, default='UTC', help_text="User's preferred timezone, e.g., 'America/New_York'")`
    *   Description: Used to display dates/times in the user's local time.
*   **`created_at`**: `DateTimeField(auto_now_add=True)`
    *   Description: Timestamp of when the profile was created.
*   **`updated_at`**: `DateTimeField(auto_now=True)`
    *   Description: Timestamp of the last update to the profile.

### 4.2. `Organization`

*   **`id`**: `BigAutoField(primary_key=True)`
    *   Description: Unique identifier for the organization.
*   **`name`**: `CharField(max_length=200, unique=True, help_text="The unique name of the organization")`
    *   Description: Must be unique across all organizations.
*   **`owner`**: `ForeignKey(settings.AUTH_USER_MODEL, related_name='owned_organizations', on_delete=models.PROTECT, help_text="The user who owns this organization")`
    *   Description: `on_delete=models.PROTECT` prevents deletion of a user who still owns an organization.
*   **`members`**: `ManyToManyField(settings.AUTH_USER_MODEL, related_name='organizations', blank=True, through='OrganizationMembership', help_text="Users who are members of this organization")`
    *   Description: Managed via the `OrganizationMembership` through model to store role information.
*   **`is_active`**: `BooleanField(default=True, help_text="Is the organization currently active?")`
    *   Description: Allows for soft-deleting or deactivating an organization.
*   **`created_at`**: `DateTimeField(auto_now_add=True)`
    *   Description: Timestamp of when the organization was created.
*   **`updated_at`**: `DateTimeField(auto_now=True)`
    *   Description: Timestamp of the last update.

#### 4.2.1. `OrganizationMembership` (Through Model)

*Constants to be defined in `models.py` (e.g., in the app where these models live):*
`ORGANIZATION_ROLE_MEMBER = 'member'`
`ORGANIZATION_ROLE_ADMIN = 'admin'`
`ORGANIZATION_ROLE_AUDITOR = 'auditor'`
`ORGANIZATION_ROLE_CHOICES = [`
    `(ORGANIZATION_ROLE_MEMBER, 'Member'),`
    `(ORGANIZATION_ROLE_ADMIN, 'Admin'),`
    `(ORGANIZATION_ROLE_AUDITOR, 'Auditor'),`
`]`

*   **`id`**: `BigAutoField(primary_key=True)`
*   **`organization`**: `ForeignKey(Organization, on_delete=models.CASCADE, related_name='membership_set')`
*   **`user`**: `ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='membership_set')` (Note: `related_name` should be unique or use `+` to suppress if not needed for reverse lookup from User directly to this intermediate model often).
*   **`role`**: `CharField(max_length=50, choices=ORGANIZATION_ROLE_CHOICES, default=ORGANIZATION_ROLE_MEMBER, help_text="Role of the user within the organization")`
*   **`date_joined`**: `DateTimeField(auto_now_add=True)`

*Meta options for `OrganizationMembership` (in `models.py`):*
`class Meta:`
    `unique_together = ('organization', 'user')`
    `verbose_name = 'Organization Membership'`
    `verbose_name_plural = 'Organization Memberships'`

### 4.3. `Project`

*   **`id`**: `BigAutoField(primary_key=True)`
    *   Description: Unique identifier for the project.
*   **`name`**: `CharField(max_length=255, help_text="Name of the project. Should be unique within an organization or for a user.")`
    *   Description: While not globally unique, it's good practice to enforce uniqueness per owner (user/org) via application logic or a custom model constraint if necessary.
*   **`description`**: `TextField(blank=True, null=True, help_text="A detailed description of the project.")`
*   **`owner_user`**: `ForeignKey(settings.AUTH_USER_MODEL, related_name='owned_projects_%(class)s', on_delete=models.CASCADE, null=True, blank=True, help_text="Individual user owning the project (if not an organizational project).")`
    *   Note: `%(class)s` in `related_name` can help ensure uniqueness if this model is subclassed or if `settings.AUTH_USER_MODEL` has other relations named `owned_projects`.
*   **`owner_organization`**: `ForeignKey('Organization', related_name='projects', on_delete=models.CASCADE, null=True, blank=True, help_text="Organization owning the project.")`
    *   Description: Links the project to an `Organization`.
*   **`is_active`**: `BooleanField(default=True, help_text="Is the project currently active?")`
    *   Description: Allows for soft-deleting or archiving a project.
*   **`created_at`**: `DateTimeField(auto_now_add=True)`
*   **`updated_at`**: `DateTimeField(auto_now=True)`

*Model Validation (to be implemented in `models.py`):*
`def clean(self):`
    `if self.owner_user and self.owner_organization:`
        `raise ValidationError("A project cannot have both an individual user owner and an organization owner.")`
    `if not self.owner_user and not self.owner_organization:`
        `raise ValidationError("A project must have either an individual user owner or an organization owner.")`

*Meta options for `Project` (in `models.py`):*
`class Meta:`
    `unique_together = (
        ('owner_user', 'name'), 
        ('owner_organization', 'name'),
    )`
    `verbose_name = 'Project'`
    `verbose_name_plural = 'Projects'`

### 4.4. `TargetAsset`

*Constants to be defined in `models.py` for `asset_type` choices:*
`ASSET_TYPE_URL = 'url'`
`ASSET_TYPE_GIT = 'git_repository'`
`ASSET_TYPE_DOCKER = 'docker_image'`
`ASSET_TYPE_FILE = 'file_upload'`
`ASSET_TYPE_IP = 'ip_address'`
`ASSET_TYPE_DOMAIN = 'domain_name'`
`# ... potentially more types ...`
`ASSET_TYPE_CHOICES = [`
    `(ASSET_TYPE_URL, 'URL'),`
    `(ASSET_TYPE_GIT, 'Git Repository'),`
    `(ASSET_TYPE_DOCKER, 'Docker Image'),`
    `(ASSET_TYPE_FILE, 'File Upload'),`
    `(ASSET_TYPE_IP, 'IP Address'),`
    `(ASSET_TYPE_DOMAIN, 'Domain Name'),`
`]`

*   **`id`**: `BigAutoField(primary_key=True)`
*   **`project`**: `ForeignKey(Project, related_name='target_assets', on_delete=models.CASCADE, help_text="The project this asset belongs to.")`
*   **`name`**: `CharField(max_length=255, blank=True, help_text="User-friendly name for this asset (e.g., 'Production API', 'Main Web App')")`
    *   Description: Optional name for easier identification of the asset within a project.
*   **`asset_type`**: `CharField(max_length=50, choices=ASSET_TYPE_CHOICES, help_text="Type of the asset being targeted.")`
*   **`identifier`**: `TextField(help_text="The main identifier for the asset (e.g., URL, git clone path, image name).")`
    *   Description: This field stores the core piece of information needed to access/scan the asset.
*   **`metadata`**: `JSONField(default=dict, blank=True, help_text="Type-specific additional details, e.g., {\"branch\": \"main\"} for git.")`
    *   Description: Flexible field to store context-specific data for different asset types.
*   **`description`**: `TextField(blank=True, null=True, help_text="Optional description for this target asset.")`
*   **`is_active`**: `BooleanField(default=True, help_text="Is this target asset currently active for scanning?")`
*   **`created_at`**: `DateTimeField(auto_now_add=True)`
*   **`updated_at`**: `DateTimeField(auto_now=True)`

*Meta options for `TargetAsset` (in `models.py`):*
`class Meta:`
    `unique_together = (
        ('project', 'identifier', 'asset_type'), # Ensures an asset is unique within a project by its ID and type
        ('project', 'name') # Optional: if name is provided, it should be unique within the project
    )`
    `ordering = ['project', 'name', 'asset_type']`
    `verbose_name = 'Target Asset'`
    `verbose_name_plural = 'Target Assets'`

### 4.5. `ToolDefinition`

*Constants to be defined in `models.py` for `tool_type` choices:*
`TOOL_TYPE_DAST = 'dast'`
`TOOL_TYPE_SAST = 'sast'`
`TOOL_TYPE_SCA = 'sca' # Software Composition Analysis`
`TOOL_TYPE_IMAGE = 'image_scanner'`
`TOOL_TYPE_SECRETS = 'secrets_scanner'`
`TOOL_TYPE_INFRA = 'iac_scanner' # Infrastructure as Code`
`TOOL_TYPE_CLOUD = 'cloud_config_scanner'`
`# ... potentially more types ...`
`TOOL_TYPE_CHOICES = [`
    `(TOOL_TYPE_DAST, 'Dynamic Application Security Testing'),`
    `(TOOL_TYPE_SAST, 'Static Application Security Testing'),`
    `(TOOL_TYPE_SCA, 'Software Composition Analysis'),`
    `(TOOL_TYPE_IMAGE, 'Container Image Scanner'),`
    `(TOOL_TYPE_SECRETS, 'Secrets Scanner'),`
    `(TOOL_TYPE_INFRA, 'Infrastructure as Code Scanner'),`
    `(TOOL_TYPE_CLOUD, 'Cloud Configuration Scanner'),`
`]`

*   **`id`**: `BigAutoField(primary_key=True)`
*   **`tool_id`**: `CharField(max_length=100, unique=True, help_text="Unique machine-readable ID, e.g., semgrep_sast")`
    *   Description: Used internally for referencing and orchestrating the tool.
*   **`name`**: `CharField(max_length=255, unique=True, help_text="User-friendly name, e.g., Semgrep SAST")`
*   **`description`**: `TextField(blank=True)`
*   **`tool_type`**: `CharField(max_length=50, choices=TOOL_TYPE_CHOICES, help_text="Category of the security tool.")`
*   **`target_asset_types`**: `JSONField(default=list, blank=True, help_text="List of TargetAsset types this tool supports, e.g., [\"git_repository\", \"file_upload\"]")`
    *   Description: Stores values from `ASSET_TYPE_CHOICES` defined for `TargetAsset`.
*   **`version`**: `CharField(max_length=50, blank=True, help_text="Version of the tool, if applicable.")`
*   **`docker_image_name`**: `CharField(max_length=255, blank=True, help_text="Name of the Docker image used to run this tool, if containerized.")`
*   **`entrypoint_command`**: `TextField(blank=True, help_text="Command to run the tool (can include placeholders for config).")`
    *   Description: E.g., `semgrep scan --config {ruleset} --json -o {output_file} {target_path}`
*   **`default_config_template`**: `JSONField(default=dict, blank=True, help_text="Default configuration parameters for the tool.")`
    *   Description: A JSON structure representing configurable options and their defaults.
*   **`result_parser_info`**: `JSONField(default=dict, blank=True, help_text="Information for parsing results, e.g., {\"format\": \"sarif\"}")`
    *   Description: Hints for the system on how to interpret the tool's output to extract findings.
*   **`is_active`**: `BooleanField(default=True, help_text="Is this tool definition available for use?")`
*   **`created_at`**: `DateTimeField(auto_now_add=True)`
*   **`updated_at`**: `DateTimeField(auto_now=True)`

*Meta options for `ToolDefinition` (in `models.py`):*
`class Meta:`
    `ordering = ['name']`
    `verbose_name = 'Tool Definition'`
    `verbose_name_plural = 'Tool Definitions'`

### 4.6. `ScanConfiguration`

*Constants to be defined for `schedule_type` choices:*
`SCHEDULE_TYPE_MANUAL = 'manual'`
`SCHEDULE_TYPE_CRON = 'cron'`
`SCHEDULE_TYPE_WEBHOOK = 'webhook'`
`SCHEDULE_TYPE_CHOICES = [`
    `(SCHEDULE_TYPE_MANUAL, 'Manual'),`
    `(SCHEDULE_TYPE_CRON, 'Scheduled (Cron)'),`
    `(SCHEDULE_TYPE_WEBHOOK, 'Webhook Triggered'),`
`]`

*   **`id`**: `BigAutoField(primary_key=True)`
*   **`project`**: `ForeignKey(Project, related_name='scan_configurations', on_delete=models.CASCADE, help_text="The project this scan configuration belongs to.")`
*   **`name`**: `CharField(max_length=255, help_text="User-friendly name, e.g., 'Daily Web App Scan', 'CI SAST Checks'.")`
*   **`description`**: `TextField(blank=True, null=True)`
*   **`target_assets`**: `ManyToManyField(TargetAsset, related_name='scan_configurations', blank=True, help_text="Specific assets to scan. If empty, may imply all compatible assets in the project based on tool compatibility.")`
    *   Description: Allows scoping a configuration to a subset of assets in a project.
*   **`tools_and_configs`**: `JSONField(default=list, help_text='List of tool IDs and their config overrides, e.g., [{\"tool_id\": \"semgrep_sast\", \"overrides\": {\"ruleset\": \"custom.yml\"}}]')`
    *   Description: Defines which tools run and their specific parameters for this configuration.
*   **`schedule_type`**: `CharField(max_length=20, choices=SCHEDULE_TYPE_CHOICES, default=SCHEDULE_TYPE_MANUAL, help_text="How this scan is triggered.")`
*   **`schedule`**: `CharField(max_length=100, blank=True, help_text="Schedule details, e.g., cron expression for 'cron' type, or webhook URL token part.")`
*   **`is_active`**: `BooleanField(default=True, help_text="Is this scan configuration enabled for triggering or scheduling?")`
*   **`created_by`**: `ForeignKey(settings.AUTH_USER_MODEL, related_name='created_scan_configurations', on_delete=models.SET_NULL, null=True, blank=True)`
*   **`last_triggered_at`**: `DateTimeField(null=True, blank=True, help_text="Timestamp of the last time this configuration was triggered to start a scan.")`
*   **`created_at`**: `DateTimeField(auto_now_add=True)`
*   **`updated_at`**: `DateTimeField(auto_now=True)`

*Meta options for `ScanConfiguration` (in `models.py`):*
`class Meta:`
    `unique_together = ('project', 'name')`
    `ordering = ['project', 'name']`
    `verbose_name = 'Scan Configuration'`
    `verbose_name_plural = 'Scan Configurations'`

### 4.7. `Scan`

*Constants to be defined for `trigger_type` and `status` choices:*
`SCAN_TRIGGER_MANUAL = 'manual'`
`SCAN_TRIGGER_SCHEDULED = 'scheduled'`
`SCAN_TRIGGER_WEBHOOK = 'webhook'`
`SCAN_TRIGGER_API = 'api'`
`SCAN_TRIGGER_TYPE_CHOICES = [`
    `(SCAN_TRIGGER_MANUAL, 'Manual'),`
    `(SCAN_TRIGGER_SCHEDULED, 'Scheduled'),`
    `(SCAN_TRIGGER_WEBHOOK, 'Webhook'),`
    `(SCAN_TRIGGER_API, 'API Triggered'),`
`]`

`SCAN_STATUS_PENDING = 'pending'`
`SCAN_STATUS_QUEUED = 'queued'`
`SCAN_STATUS_RUNNING = 'running'`
`SCAN_STATUS_COMPLETED = 'completed'`
`SCAN_STATUS_FAILED = 'failed' # Failure in one or more tools but scan process itself finished`
`SCAN_STATUS_ERROR = 'error' # System error preventing scan execution or completion`
`SCAN_STATUS_CANCELLED = 'cancelled'`
`SCAN_STATUS_CHOICES = [`
    `(SCAN_STATUS_PENDING, 'Pending'),`
    `(SCAN_STATUS_QUEUED, 'Queued'),`
    `(SCAN_STATUS_RUNNING, 'Running'),`
    `(SCAN_STATUS_COMPLETED, 'Completed'),`
    `(SCAN_STATUS_FAILED, 'Failed'),`
    `(SCAN_STATUS_ERROR, 'Error'),`
    `(SCAN_STATUS_CANCELLED, 'Cancelled'),`
`]`

*   **`id`**: `BigAutoField(primary_key=True)`
*   **`scan_configuration`**: `ForeignKey(ScanConfiguration, related_name='scans', on_delete=models.CASCADE, help_text="The configuration that this scan execution is based on.")`
*   **`project`**: `ForeignKey(Project, related_name='scans', on_delete=models.CASCADE, help_text="Denormalized from ScanConfiguration for easier querying/filtering of scans by project.")`
    *   Note: Ensure this is kept in sync if `ScanConfiguration.project` could ever change, or populate on save.
*   **`trigger_type`**: `CharField(max_length=20, choices=SCAN_TRIGGER_TYPE_CHOICES, help_text="How the scan was initiated.")`
*   **`triggered_by_user`**: `ForeignKey(settings.AUTH_USER_MODEL, related_name='triggered_scans', on_delete=models.SET_NULL, null=True, blank=True, help_text="User who manually triggered the scan, if applicable.")`
*   **`status`**: `CharField(max_length=20, choices=SCAN_STATUS_CHOICES, default=SCAN_STATUS_PENDING, db_index=True, help_text="Current status of the scan execution.")`
*   **`start_time`**: `DateTimeField(null=True, blank=True, db_index=True, help_text="Timestamp when the scan processing actually started.")`
*   **`end_time`**: `DateTimeField(null=True, blank=True, help_text="Timestamp when the scan processing completed or terminated.")`
*   **`celery_task_id`**: `CharField(max_length=255, blank=True, null=True, db_index=True, help_text="ID of the Celery task executing this scan, if applicable.")`
*   **`progress_percentage`**: `IntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(100)], null=True, blank=True, help_text="Overall progress of the scan execution (0-100).")`
*   **`summary_data`**: `JSONField(default=dict, blank=True, help_text="Aggregated summary, e.g., {\"total_findings\": 10, \"critical\": 2, \"high\": 3}")`
    *   Description: Can store counts of findings by severity, or other high-level results.
*   **`created_at`**: `DateTimeField(auto_now_add=True, db_index=True)`
*   **`updated_at`**: `DateTimeField(auto_now=True)`

*Meta options for `Scan` (in `models.py`):*
`class Meta:`
    `ordering = ['project', '-created_at']`
    `verbose_name = 'Scan'`
    `verbose_name_plural = 'Scans'`

### 4.8. `ScanToolResult`

*Constants to be defined for `status` choices for a tool run:*
`TOOL_SCAN_STATUS_PENDING = 'pending'`
`TOOL_SCAN_STATUS_CONFIGURING = 'configuring'`
`TOOL_SCAN_STATUS_RUNNING = 'running'`
`TOOL_SCAN_STATUS_COMPLETED = 'completed' # Tool ran, results (if any) are processed`
`TOOL_SCAN_STATUS_NO_FINDINGS = 'no_findings' # Tool ran successfully but found nothing`
`TOOL_SCAN_STATUS_FAILED = 'failed' # Tool execution failed (e.g., crash, bad exit code)`
`TOOL_SCAN_STATUS_TIMED_OUT = 'timed_out'`
`TOOL_SCAN_STATUS_SKIPPED = 'skipped' # e.g., if target asset type not compatible`
`TOOL_SCAN_STATUS_CHOICES = [`
    `(TOOL_SCAN_STATUS_PENDING, 'Pending'),`
    `(TOOL_SCAN_STATUS_CONFIGURING, 'Configuring'),`
    `(TOOL_SCAN_STATUS_RUNNING, 'Running'),`
    `(TOOL_SCAN_STATUS_COMPLETED, 'Completed'),`
    `(TOOL_SCAN_STATUS_NO_FINDINGS, 'Completed (No Findings)'),`
    `(TOOL_SCAN_STATUS_FAILED, 'Failed'),`
    `(TOOL_SCAN_STATUS_TIMED_OUT, 'Timed Out'),`
    `(TOOL_SCAN_STATUS_SKIPPED, 'Skipped'),`
`]`

*   **`id`**: `BigAutoField(primary_key=True)`
*   **`scan`**: `ForeignKey(Scan, related_name='tool_results', on_delete=models.CASCADE, help_text="The parent scan this tool result belongs to.")`
*   **`tool_definition`**: `ForeignKey(ToolDefinition, related_name='scan_results', on_delete=models.PROTECT, help_text="The specific tool that produced this result.")`
    *   Note: `on_delete=models.PROTECT` to prevent deleting a `ToolDefinition` if results from it exist.
*   **`status`**: `CharField(max_length=20, choices=TOOL_SCAN_STATUS_CHOICES, default=TOOL_SCAN_STATUS_PENDING, db_index=True, help_text="Status of this specific tool's execution within the scan.")`
*   **`start_time`**: `DateTimeField(null=True, blank=True, help_text="Timestamp when this specific tool started processing.")`
*   **`end_time`**: `DateTimeField(null=True, blank=True, help_text="Timestamp when this specific tool finished processing.")`
*   **`raw_output_path`**: `FileField(upload_to='scan_tool_outputs/%Y/%m/%d/', blank=True, null=True, max_length=500, help_text="Path to the raw output file from the tool, if stored as a file.")`
    *   Description: Stored in Django's media storage.
*   **`raw_output_snippet`**: `TextField(blank=True, null=True, help_text="Short snippet of raw output, useful for quick error diagnosis or summary.")`
*   **`summary`**: `JSONField(default=dict, blank=True, help_text="Parsed summary from the tool, e.g., {\"findings_count\": 5, \"errors\": 0}.")`
*   **`error_message`**: `TextField(blank=True, null=True, help_text="Detailed error message if the tool execution failed.")`
*   **`created_at`**: `DateTimeField(auto_now_add=True)`
*   **`updated_at`**: `DateTimeField(auto_now=True)`

*Meta options for `ScanToolResult` (in `models.py`):*
`class Meta:`
    `ordering = ['scan', 'tool_definition__name']`
    `unique_together = ('scan', 'tool_definition') # A tool should only run once per scan instance`
    `verbose_name = 'Scan Tool Result'`
    `verbose_name_plural = 'Scan Tool Results'`

### 4.9. `Finding`

*Constants to be defined for `severity`, `status`, and `confidence` choices:*
`FINDING_SEVERITY_CRITICAL = 'critical'`
`FINDING_SEVERITY_HIGH = 'high'`
`FINDING_SEVERITY_MEDIUM = 'medium'`
`FINDING_SEVERITY_LOW = 'low'`
`FINDING_SEVERITY_INFO = 'informational'`
`FINDING_SEVERITY_UNKNOWN = 'unknown'`
`FINDING_SEVERITY_CHOICES = [`
    `(FINDING_SEVERITY_CRITICAL, 'Critical'),`
    `(FINDING_SEVERITY_HIGH, 'High'),`
    `(FINDING_SEVERITY_MEDIUM, 'Medium'),`
    `(FINDING_SEVERITY_LOW, 'Low'),`
    `(FINDING_SEVERITY_INFO, 'Informational'),`
    `(FINDING_SEVERITY_UNKNOWN, 'Unknown'),`
`]`

`FINDING_STATUS_NEW = 'new'`
`FINDING_STATUS_CONFIRMED = 'confirmed' # Triaged as a valid issue`
`FINDING_STATUS_FALSE_POSITIVE = 'false_positive' # Triaged as not an issue`
`FINDING_STATUS_RESOLVED = 'resolved' # Fix has been implemented and verified`
`FINDING_STATUS_IGNORED = 'ignored' # Valid, but accepted risk or won't fix`
`FINDING_STATUS_AUTO_RESOLVED = 'auto_resolved' # System detected fix (e.g., no longer present in subsequent scan)`
`FINDING_STATUS_REOPENED = 'reopened' # Previously resolved/ignored, but has reappeared`
`FINDING_STATUS_CHOICES = [`
    `(FINDING_STATUS_NEW, 'New'),`
    `(FINDING_STATUS_CONFIRMED, 'Confirmed'),`
    `(FINDING_STATUS_FALSE_POSITIVE, 'False Positive'),`
    `(FINDING_STATUS_RESOLVED, 'Resolved'),`
    `(FINDING_STATUS_IGNORED, 'Ignored (Accepted Risk)'),`
    `(FINDING_STATUS_AUTO_RESOLVED, 'Auto-Resolved'),`
    `(FINDING_STATUS_REOPENED, 'Reopened'),`
`]`

`FINDING_CONFIDENCE_HIGH = 'high'`
`FINDING_CONFIDENCE_MEDIUM = 'medium'`
`FINDING_CONFIDENCE_LOW = 'low'`
`FINDING_CONFIDENCE_CHOICES = [`
    `(FINDING_CONFIDENCE_HIGH, 'High'),`
    `(FINDING_CONFIDENCE_MEDIUM, 'Medium'),`
    `(FINDING_CONFIDENCE_LOW, 'Low'),`
`]`

*   **`id`**: `BigAutoField(primary_key=True)`
*   **`scan_tool_result`**: `ForeignKey(ScanToolResult, related_name='findings', on_delete=models.CASCADE, help_text="The specific tool run that identified this finding.")`
*   **`project`**: `ForeignKey(Project, related_name='findings', on_delete=models.CASCADE, help_text="Denormalized: Project associated with this finding for easier querying.")`
    *   Note: This would be populated from `scan_tool_result.scan.project`.
*   **`title`**: `CharField(max_length=512, help_text="A concise title for the finding.")`
*   **`description`**: `TextField(help_text="Detailed description of the vulnerability, its impact, and context.")`
*   **`severity`**: `CharField(max_length=20, choices=FINDING_SEVERITY_CHOICES, default=FINDING_SEVERITY_UNKNOWN, db_index=True)`
*   **`status`**: `CharField(max_length=30, choices=FINDING_STATUS_CHOICES, default=FINDING_STATUS_NEW, db_index=True, help_text="The current triage status of the finding.")`
*   **`confidence`**: `CharField(max_length=20, choices=FINDING_CONFIDENCE_CHOICES, blank=True, null=True, db_index=True, help_text="Tool's confidence in this finding.")`
*   **`cve_id`**: `CharField(max_length=50, blank=True, null=True, db_index=True, help_text="CVE identifier, e.g., CVE-2021-44228")`
*   **`cwe_id`**: `CharField(max_length=50, blank=True, null=True, db_index=True, help_text="CWE identifier, e.g., CWE-79")`
*   **`epss_score`**: `FloatField(null=True, blank=True, help_text="EPSS (Exploit Prediction Scoring System) score, if available.")`
*   **`location_data`**: `JSONField(default=dict, blank=True, help_text='Structured location: e.g., {\"file_path\": \"app/views.py\", \"line\": 10}')`
*   **`evidence_snippet`**: `TextField(blank=True, null=True, help_text="Code snippet or other evidence demonstrating the finding.")`
*   **`remediation_guidance`**: `TextField(blank=True, null=True, help_text="Guidance or suggestions on how to fix the vulnerability.")`
*   **`unique_identifier_from_tool`**: `CharField(max_length=1024, blank=True, null=True, db_index=True, help_text="Raw unique ID for this finding from the tool, for de-duplication reference.")`
*   **`fingerprint`**: `CharField(max_length=128, db_index=True, help_text="SecuLite-generated stable fingerprint for tracking this unique issue across scans.")`
    *   Note: This should be unique per project for a given logical vulnerability.
*   **`is_false_positive`**: `BooleanField(default=False, db_index=True, help_text="Explicitly marked as a false positive by a user.")`
*   **`is_ignored`**: `BooleanField(default=False, db_index=True, help_text="User has marked this finding to be ignored (e.g., accepted risk).")`
*   **`resolution_notes`**: `TextField(blank=True, null=True, help_text="Notes from user about resolution or triage decision.")`
*   **`first_seen_at_scan`**: `ForeignKey(Scan, related_name='first_occurrence_findings', on_delete=models.SET_NULL, null=True, blank=True, help_text="The scan instance where this unique finding (by fingerprint) was first observed.")`
*   **`last_seen_at_scan`**: `ForeignKey(Scan, related_name='last_occurrence_findings', on_delete=models.SET_NULL, null=True, blank=True, help_text="The most recent scan instance where this unique finding (by fingerprint) was observed.")`
*   **`resolved_at_scan`**: `ForeignKey(Scan, related_name='resolved_findings', on_delete=models.SET_NULL, null=True, blank=True, help_text="The scan instance where this unique finding (by fingerprint) was confirmed as resolved.")`
*   **`assigned_to_user`**: `ForeignKey(settings.AUTH_USER_MODEL, related_name='assigned_findings', on_delete=models.SET_NULL, null=True, blank=True)`
*   **`due_date`**: `DateField(null=True, blank=True, help_text="Target date for resolving this finding.")`
*   **`tags`**: `JSONField(default=list, blank=True, help_text='Custom tags, e.g., [\"pci\", \"gdpr\", \"bug_bounty\"].')`
*   **`created_at`**: `DateTimeField(auto_now_add=True, db_index=True)`
*   **`updated_at`**: `DateTimeField(auto_now=True)`

*Meta options for `Finding` (in `models.py`):*
`class Meta:`
    `ordering = ['project', '-severity', '-created_at']`
    `unique_together = ('scan_tool_result', 'fingerprint')) # A finding (by fingerprint) should be unique per tool result if the tool could report it multiple ways slightly differently. More robustly, fingerprint should be unique per project over time.`
    `# Consider a more complex unique_together or model validation for ('project', 'fingerprint') if a finding should be truly unique across all scans for a project.`
    `verbose_name = 'Finding'`
    `verbose_name_plural = 'Findings'`

---

## 5. Database Schema Considerations

*(This section will list any specific database considerations, e.g.:)*
*   **Indexing:** Identify fields that will be frequently queried and require database indexes for performance (e.g., `Finding.status`, `Scan.start_time`, `TargetAsset.asset_identifier`).
*   **JSONField Usage:** Note where `JSONField` is used (e.g., `TargetAsset.metadata`, `ScanConfiguration.tool_specific_configurations`) and any implications for querying.
*   **Data Integrity:** Reinforce use of `ForeignKey` constraints for relational integrity.
*   **Large Text/Binary Data:** Considerations for storing raw scan outputs (e.g., store paths to files vs. direct LOBs in DB, though paths are generally preferred for Django apps).

--- 