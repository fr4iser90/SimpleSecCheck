from django.db import models
from django.contrib.auth.models import User
import secrets
import hashlib
from django.conf import settings
from django.utils import timezone

class Project(models.Model):
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True, null=True)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='owned_projects', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    # Add members through ProjectMembership
    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through='ProjectMembership',
        related_name='project_memberships'
    )

    def __str__(self):
        return self.name

class ProjectMembership(models.Model):
    class Role(models.TextChoices):
        MANAGER = 'manager', 'Manager'
        DEVELOPER = 'developer', 'Developer'
        VIEWER = 'viewer', 'Viewer'

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    role = models.CharField(
        max_length=10,
        choices=Role.choices,
        default=Role.VIEWER,
    )
    date_joined = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'project') # User can only have one role per project
        ordering = ['project__name', 'user__username']

    def __str__(self):
        return f"{self.user.username} - {self.project.name} ({self.get_role_display()})"

class ScanTarget(models.Model):
    # e.g., URL, IP, hostname, repository URI
    target_value = models.CharField(max_length=1024, unique=True)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.target_value

class TargetGroup(models.Model):
    name = models.CharField(max_length=200, unique=True)
    description = models.TextField(blank=True, null=True)
    targets = models.ManyToManyField(ScanTarget, related_name='target_groups')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class SecurityTool(models.Model):
    name = models.CharField(max_length=100, unique=True) # e.g., "Bandit", "ESLint", "Trivy"
    description = models.TextField(blank=True, null=True)
    # Further fields like version, configuration_template (JSON) could be added
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class ScanConfiguration(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    project = models.ForeignKey(Project, related_name='scan_configurations', on_delete=models.CASCADE)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='created_scan_configurations', on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Defines if targets are part of this configuration or need to be provided at scan time
    has_predefined_targets = models.BooleanField(default=False)
    # Stores structured target information, e.g., repo URL, paths, type
    target_details_json = models.JSONField(blank=True, null=True, help_text="Structured target info, e.g., repo URL, paths. Used if has_predefined_targets is true.")
    # Stores tool-specific settings, e.g., which linters to run, severity thresholds
    tool_configurations_json = models.JSONField(blank=True, null=True, help_text="Tool-specific settings, e.g., Bandit severity, Semgrep rules.")

    def __str__(self):
        return f"{self.name} (Project: {self.project.name})"

    class Meta:
        unique_together = ('project', 'name')
        ordering = ['project__name', 'name']

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    bio = models.TextField(blank=True, null=True)
    # Placeholder for a more robust API key management system later
    # For now, a simple field to indicate if they *can* have an API key or a simple key itself.
    # In a real system, API keys would be separate, hashed, and managed more securely.
    api_key_placeholder = models.CharField(max_length=128, blank=True, null=True, help_text="Placeholder for API key info/management")
    # Example: Notification preferences (can be a JSONField for more complex settings)
    receive_email_notifications = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.user.username

class ApiKey(models.Model):
    key = models.CharField(max_length=64, unique=True, editable=False, default='')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='api_keys', on_delete=models.CASCADE)
    name = models.CharField(max_length=100, blank=True, help_text="A friendly name for this API key.")
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(blank=True, null=True, help_text="Optional: Set an expiration date for the key.")
    last_used = models.DateTimeField(blank=True, null=True, editable=False)
    is_active = models.BooleanField(default=True)
    # Potentially link to a project if keys are project-specific
    # project = models.ForeignKey(Project, related_name='project_api_keys', on_delete=models.CASCADE, blank=True, null=True)

    def __str__(self):
        return f"{self.user.username} - {self.name or self.key[:8] + '...'}"

# New Models for Scan Jobs and Results (G8.1)

class ScanJobStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending' # Job created, not yet sent to Celery
    QUEUED = 'QUEUED', 'Queued'   # Task sent to Celery broker
    RUNNING = 'RUNNING', 'Running' # Task started by a Celery worker
    COMPLETED = 'COMPLETED', 'Completed' # Task finished successfully
    FAILED = 'FAILED', 'Failed'     # Task execution failed
    CANCELLED = 'CANCELLED', 'Cancelled' # User initiated cancellation (future feature)
    TIMEOUT = 'TIMEOUT', 'Timeout'     # Task exceeded its time limit (future feature)

class ScanJob(models.Model):
    project = models.ForeignKey(Project, related_name='scan_jobs', on_delete=models.CASCADE)
    scan_configuration = models.ForeignKey(ScanConfiguration, related_name='scan_jobs', on_delete=models.SET_NULL, null=True, blank=True, help_text="Configuration used for this job, if any.")
    initiator = models.ForeignKey(User, related_name='initiated_scan_jobs', on_delete=models.SET_NULL, null=True)
    celery_task_id = models.CharField(max_length=255, null=True, blank=True, unique=True, db_index=True)
    status = models.CharField(
        max_length=20,
        choices=ScanJobStatus.choices,
        default=ScanJobStatus.PENDING
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    started_timestamp = models.DateTimeField(null=True, blank=True)
    completed_timestamp = models.DateTimeField(null=True, blank=True)
    # Potentially store selected targets if not using a ScanConfiguration or for ad-hoc scans
    # custom_targets = models.JSONField(null=True, blank=True, help_text="For ad-hoc scans, list of targets if not from configuration")

    # New fields for CI/CD context
    commit_hash = models.CharField(max_length=255, null=True, blank=True, db_index=True)
    branch_name = models.CharField(max_length=255, null=True, blank=True, db_index=True)
    repository_url = models.URLField(max_length=2000, null=True, blank=True)
    ci_build_id = models.CharField(max_length=255, null=True, blank=True, db_index=True)
    triggered_by_ci = models.BooleanField(default=False)

    def __str__(self):
        return f"Scan Job {self.id} for {self.project.name} - Status: {self.status}"

    class Meta:
        ordering = ['-created_at']

class ScanResult(models.Model):
    scan_job = models.ForeignKey(ScanJob, related_name='results', on_delete=models.CASCADE)
    tool_name = models.CharField(max_length=100, help_text="Name of the security tool that produced this result, e.g., Bandit")
    # If linked to a SecurityTool model instance:
    # security_tool = models.ForeignKey(SecurityTool, on_delete=models.SET_NULL, null=True, blank=True)
    summary_data = models.JSONField(null=True, blank=True, help_text="Summary of findings, e.g., severity counts")
    raw_output = models.TextField(blank=True, null=True, help_text="Full raw output from the tool, if stored")
    findings = models.JSONField(default=list, help_text="Structured list of findings/vulnerabilities")
    error_message = models.TextField(blank=True, null=True, help_text="Error message if the tool failed for this result part")
    timestamp = models.DateTimeField(auto_now_add=True, help_text="When this specific result was recorded")

    def __str__(self):
        return f"Result for {self.scan_job_id} by {self.tool_name} at {self.timestamp}"

    class Meta:
        ordering = ['-timestamp']
