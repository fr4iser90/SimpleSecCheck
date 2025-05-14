from rest_framework import serializers
from .models import Project, ScanTarget, TargetGroup, SecurityTool, ScanConfiguration, UserProfile, ApiKey, ScanResult, ScanJob, ProjectMembership
from django.contrib.auth import get_user_model

User = get_user_model()

class UserSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email']

class ProjectMembershipSerializer(serializers.ModelSerializer):
    user = UserSimpleSerializer(read_only=True)
    class Meta:
        model = ProjectMembership
        fields = ['id', 'user', 'project', 'role', 'date_joined']
        read_only_fields = ['project', 'date_joined']

# New Serializer for Write operations on ProjectMembership
class ProjectMembershipWriteSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())
    # Project will be implicitly set or validated in the ViewSet based on context
    # to ensure the requesting user has rights to manage members for that project.
    # For create, project_id might come from URL or a validated request field.
    # We make it writable here, but ViewSet must control it.
    project = serializers.PrimaryKeyRelatedField(queryset=Project.objects.all())

    class Meta:
        model = ProjectMembership
        fields = ['id', 'user', 'project', 'role'] # date_joined is auto_now_add
        # On update, we might want to make user and project read-only.
        # This can be handled in the viewset's get_serializer_class or by separate update serializer.

    def validate(self, data):
        project = data.get('project')
        user = data.get('user')
        role = data.get('role')

        # For updates (instance exists)
        if self.instance:
            if self.instance.project != project:
                raise serializers.ValidationError("Cannot change the project of an existing membership.")
            if self.instance.user != user:
                raise serializers.ValidationError("Cannot change the user of an existing membership.")
            # Prevent demoting the last manager/owner or self-demotion from critical role without alternatives.
            # This complex logic is better suited for the ViewSet or model's save method.
        else: # For creates
            if ProjectMembership.objects.filter(project=project, user=user).exists():
                raise serializers.ValidationError(
                    f"User {user.username} is already a member of project {project.name}."
                )
        return data

class ProjectSerializer(serializers.ModelSerializer):
    owner = UserSimpleSerializer(read_only=True)
    project_memberships = ProjectMembershipSerializer(source='projectmembership_set', many=True, read_only=True)
    can_trigger_scan = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = ['id', 'name', 'description', 'owner', 'created_at', 'updated_at', 'project_memberships', 'can_trigger_scan']
        read_only_fields = ['owner', 'created_at', 'updated_at', 'project_memberships']

    def get_can_trigger_scan(self, obj):
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            user = request.user
            if user.is_superuser:
                return True
            # Check if the user is a member of the project with a role that allows scanning
            try:
                membership = ProjectMembership.objects.get(project=obj, user=user)
                return membership.role in [ProjectMembership.RoleChoices.DEVELOPER,
                                           ProjectMembership.RoleChoices.MANAGER,
                                           ProjectMembership.RoleChoices.OWNER]
            except ProjectMembership.DoesNotExist:
                return False
        return False

class ScanTargetSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScanTarget
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')

class TargetGroupSerializer(serializers.ModelSerializer):
    targets = ScanTargetSerializer(many=True, read_only=True)
    target_ids = serializers.PrimaryKeyRelatedField(
        queryset=ScanTarget.objects.all(), source='targets', many=True, write_only=True, required=False
    )

    class Meta:
        model = TargetGroup
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')

class SecurityToolSerializer(serializers.ModelSerializer):
    class Meta:
        model = SecurityTool
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')

class ScanConfigurationSerializer(serializers.ModelSerializer):
    created_by = UserSimpleSerializer(read_only=True)
    project_name = serializers.CharField(source='project.name', read_only=True)

    class Meta:
        model = ScanConfiguration
        fields = [
            'id', 'name', 'description', 'project', 'project_name', 'created_by', 
            'has_predefined_targets', 'target_details_json', 'tool_configurations_json',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_by', 'created_at', 'updated_at', 'project_name']
    
    def validate_project(self, value):
        user = self.context['request'].user
        if not user.is_superuser and value.owner != user:
            raise serializers.ValidationError("You do not have permission to manage configurations for this project.")
        return value

class ApiKeySerializer(serializers.ModelSerializer):
    user = UserSimpleSerializer(read_only=True)

    class Meta:
        model = ApiKey
        fields = ['id', 'user', 'name', 'key', 'created_at', 'expires_at', 'last_used', 'is_active']
        read_only_fields = ['user', 'key', 'created_at', 'last_used']

class ScanResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScanResult
        fields = '__all__'

class ScanJobSerializer(serializers.ModelSerializer):
    initiated_by = UserSimpleSerializer(read_only=True)
    project_name = serializers.CharField(source='project.name', read_only=True)
    scan_configuration_name = serializers.CharField(source='scan_configuration.name', read_only=True, allow_null=True)
    results = ScanResultSerializer(many=True, read_only=True)

    project = serializers.PrimaryKeyRelatedField(queryset=Project.objects.all())
    scan_configuration = serializers.PrimaryKeyRelatedField(
        queryset=ScanConfiguration.objects.all(), 
        required=False, 
        allow_null=True
    )

    class Meta:
        model = ScanJob
        fields = [
            'id', 'project', 'project_name', 'scan_configuration', 'scan_configuration_name',
            'target_info_json', 'tool_settings_json', 'status', 'celery_task_id', 
            'initiated_by', 'created_at', 'started_timestamp', 'completed_timestamp',
            'results',
            'commit_hash', 'branch_name', 'repository_url', 'ci_build_id', 'triggered_by_ci'
        ]
        read_only_fields = [
            'id',
            'project_name', 
            'scan_configuration_name', 
            'status',
            'celery_task_id',
            'initiated_by',
            'created_at', 'started_timestamp', 'completed_timestamp',
            'results'
        ]

    def validate(self, data):
        project = data.get('project')
        scan_configuration = data.get('scan_configuration')

        if project and scan_configuration:
            if scan_configuration.project != project:
                raise serializers.ValidationError(
                    {"scan_configuration": "This scan configuration does not belong to the selected project."}
                )
        
        return data

class UserProfileSerializer(serializers.ModelSerializer):
    user = UserSimpleSerializer(read_only=True)
    class Meta:
        model = UserProfile
        fields = ['id', 'user', 'bio', 'profile_picture_url', 'preferences']
        read_only_fields = ['user']

class CIScanTriggerSerializer(serializers.Serializer):
    project = serializers.PrimaryKeyRelatedField(
        queryset=Project.objects.all(),
        help_text="ID of the project to associate the scan with."
    )
    scan_configuration = serializers.PrimaryKeyRelatedField(
        queryset=ScanConfiguration.objects.all(),
        help_text="ID of the scan configuration to use."
    )
    commit_hash = serializers.CharField(
        required=False, allow_blank=True, max_length=255,
        help_text="Commit hash from SCM."
    )
    branch_name = serializers.CharField(
        required=False, allow_blank=True, max_length=255,
        help_text="Branch name from SCM."
    )
    repository_url = serializers.URLField(
        required=False, allow_blank=True, max_length=2000,
        help_text="Repository URL from SCM."
    )
    ci_build_id = serializers.CharField(
        required=False, allow_blank=True, max_length=255,
        help_text="CI build ID or number."
    )

    def validate(self, data):
        project = data.get('project')
        scan_config = data.get('scan_configuration')

        if project and scan_config:
            if scan_config.project != project:
                raise serializers.ValidationError(
                    "The provided Scan Configuration does not belong to the specified Project."
                )
        return data 