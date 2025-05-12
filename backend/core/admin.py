from django.contrib import admin
from .models import (
    Project, ScanTarget, TargetGroup, SecurityTool, ScanConfiguration, 
    UserProfile, ApiKey,
    ScanJob, ScanResult
)

# Basic admin registrations
admin.site.register(Project)
admin.site.register(ScanTarget)
admin.site.register(TargetGroup)
admin.site.register(SecurityTool)
admin.site.register(ScanConfiguration)
admin.site.register(UserProfile)

# Custom Admin for APIKey to show more fields and manage them
@admin.register(ApiKey)
class ApiKeyAdmin(admin.ModelAdmin):
    list_display = ('user', 'name', 'key_display', 'created_at', 'expires_at', 'is_active', 'last_used')
    search_fields = ('user__username', 'name', 'key')
    list_filter = ('is_active', 'created_at', 'expires_at')
    readonly_fields = ('key', 'last_used', 'created_at') # key and last_used are editable=False in model
    
    def key_display(self, obj):
        return f"{obj.key[:8]}..." if obj.key else "N/A"
    key_display.short_description = "Key (Prefix)"

# Admin for ScanJob
@admin.register(ScanJob)
class ScanJobAdmin(admin.ModelAdmin):
    list_display = ('id', 'project', 'scan_configuration', 'status', 'celery_task_id', 'initiator', 'created_at', 'completed_timestamp')
    search_fields = ('project__name', 'celery_task_id', 'initiator__username')
    list_filter = ('status', 'project', 'created_at')
    readonly_fields = ('celery_task_id', 'created_at', 'started_timestamp', 'completed_timestamp')

# Admin for ScanResult
@admin.register(ScanResult)
class ScanResultAdmin(admin.ModelAdmin):
    list_display = ('scan_job_id_display', 'tool_name', 'timestamp', 'has_error') # Renamed scan_job_id to scan_job_id_display
    search_fields = ('scan_job__id', 'tool_name')
    list_filter = ('tool_name', 'timestamp')
    readonly_fields = ('timestamp',)

    def scan_job_id_display(self, obj):
        return obj.scan_job.id
    scan_job_id_display.short_description = 'Scan Job ID'
    scan_job_id_display.admin_order_field = 'scan_job__id'

    def has_error(self, obj):
        return bool(obj.error_message)
    has_error.boolean = True
    has_error.short_description = 'Error Occurred'
