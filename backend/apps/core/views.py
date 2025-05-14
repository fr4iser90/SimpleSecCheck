from django.shortcuts import render, get_object_or_404
from rest_framework import viewsets, permissions, mixins, status
from rest_framework.response import Response
from django.db import models
from .models import (
    Project, ScanTarget, TargetGroup, SecurityTool, ScanConfiguration, 
    UserProfile, ApiKey, ScanJob, ScanJobStatus, ScanResult, ProjectMembership
)
from .serializers import (
    ProjectSerializer, ScanTargetSerializer, TargetGroupSerializer, 
    SecurityToolSerializer, ScanConfigurationSerializer, UserProfileSerializer,
    ApiKeySerializer, ScanJobSerializer, ScanResultSerializer,
    ProjectMembershipSerializer, ProjectMembershipWriteSerializer,
    UserSimpleSerializer, CIScanTriggerSerializer
)
# Import new permission classes
from .permissions import (
    IsSuperUser, IsProjectOwner, 
    IsProjectManager, IsProjectDeveloperOrHigher, IsProjectViewerOrHigher,
    CanManageOwnApiKey, CanManageProjectMembers,
    IsAuthenticatedAndHasAccessToProject, HasActiveApiKey
)
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from celery.result import AsyncResult
from .tasks import execute_scan_job, simulate_bandit_scan # Ensure both are imported
from django.contrib.auth import get_user_model
from .authentication import ApiKeyAuthentication # Import the custom authentication class
# Docker API Integration Imports
from rest_framework.views import APIView
from .docker_service import list_running_containers, get_container_code_paths, get_grouped_docker_compose_projects # Added get_grouped_docker_compose_projects
# End Docker API Integration Imports
User = get_user_model()

# Create your views here.

# Removing the old IsOwnerOrReadOnly as we have more specific ones now
# class IsOwnerOrReadOnly(permissions.BasePermission):
# ... (old code was here)

class ProjectViewSet(viewsets.ModelViewSet):
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer
    permission_classes = [IsAuthenticated] # Default for list and create

    def get_permissions(self):
        """
        Instantiates and returns the list of permissions that this view requires.
        Owners/Managers can do anything. Developers can read. Authenticated users can list/create.
        """
        if self.action in ['list', 'create']:
            self.permission_classes = [permissions.IsAuthenticated] # Any authenticated user can list or create projects
        elif self.action in ['retrieve', 'update', 'partial_update', 'destroy']:
            # For specific project instances, check if user is owner or manager
            self.permission_classes = [permissions.IsAuthenticated, IsProjectOwner]
        else:
            # Default to deny all for any other actions
            self.permission_classes = [permissions.DenyAll]
        return super().get_permissions()

    def perform_create(self, serializer):
        """Ensure the user creating the project is set as its owner and create a default scan configuration."""
        project = serializer.save(owner=self.request.user)
        ProjectMembership.objects.create(user=self.request.user, project=project, role=ProjectMembership.Role.MANAGER)

        target_details_for_scan_config = {}

        docker_compose_project_name = self.request.data.get('selected_compose_project_name')
        container_targets_data = self.request.data.get('container_targets')

        if docker_compose_project_name and isinstance(container_targets_data, list):
            target_details_for_scan_config['compose_project_name'] = docker_compose_project_name
            processed_containers = []
            for container_data in container_targets_data:
                if isinstance(container_data, dict) and \
                   all(key in container_data for key in ['id', 'name', 'image', 'host_code_path']):
                    processed_containers.append({
                        "id": container_data.get('id'),
                        "name": container_data.get('name'),
                        "image": container_data.get('image'),
                        "host_code_path": container_data.get('host_code_path')
                    })
                else:
                    print(f"Warning: Malformed container data received for project {project.id}: {container_data}")
            target_details_for_scan_config['containers'] = processed_containers
        else:
            if project.codebase_path_or_url:
                value = project.codebase_path_or_url
                if value.startswith(('http://', 'https://', 'git@', 'ssh://')):
                    target_details_for_scan_config['codebase_git'] = value
                elif value.startswith('/'): 
                    target_details_for_scan_config['codebase_local_path'] = value
                else: 
                    target_details_for_scan_config['codebase_local_path'] = value
                    print(f"Warning: codebase_path_or_url '{value}' for project {project.id} is not a clear URL or absolute path, treating as local path.")

        if project.web_app_url:
            target_details_for_scan_config['primary_web_app_url'] = project.web_app_url
        
        has_predefined_targets = bool(
            target_details_for_scan_config.get('containers') or \
            target_details_for_scan_config.get('codebase_git') or \
            target_details_for_scan_config.get('codebase_local_path') or \
            target_details_for_scan_config.get('primary_web_app_url')
        )

        ScanConfiguration.objects.create(
            project=project,
            name=f"Default Configuration for {project.name}",
            description="Automatically created default scan configuration. Please review and customize targets and tools.",
            target_details_json=target_details_for_scan_config if target_details_for_scan_config else None,
            tool_configurations_json=None, 
            created_by=self.request.user,
            has_predefined_targets=has_predefined_targets
        )

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return Project.objects.all().prefetch_related('projectmembership_set__user')
        
        # Users can see projects they own or are members of
        return Project.objects.filter(
            models.Q(owner=user) | models.Q(projectmembership__user=user)
        ).distinct().prefetch_related('projectmembership_set__user')

class ScanTargetViewSet(viewsets.ModelViewSet):
    queryset = ScanTarget.objects.all()
    serializer_class = ScanTargetSerializer
    # Access to targets might be restricted based on project membership eventually
    permission_classes = [permissions.IsAuthenticated] 

class TargetGroupViewSet(viewsets.ModelViewSet):
    queryset = TargetGroup.objects.all()
    serializer_class = TargetGroupSerializer
    # Access to target groups might be restricted based on project membership eventually
    permission_classes = [IsAuthenticated]

class SecurityToolViewSet(viewsets.ModelViewSet):
    queryset = SecurityTool.objects.all()
    serializer_class = SecurityToolSerializer
    permission_classes = [IsSuperUser] # Only Superusers can manage Security Tools

    # Optional: Add custom actions if needed, e.g., for tool-specific operations.

class ScanConfigurationViewSet(viewsets.ModelViewSet):
    queryset = ScanConfiguration.objects.all()
    serializer_class = ScanConfigurationSerializer
    permission_classes = [IsAuthenticated] # Base permission

    def get_permissions(self):
        if self.action == 'create':
            # To create, user must be developer or higher for the project
            return [IsAuthenticated(), IsProjectDeveloperOrHigher()]
        elif self.action == 'retrieve':
            # To retrieve, user must be viewer or higher for the project
            return [IsAuthenticated(), IsProjectViewerOrHigher()]
        elif self.action in ['update', 'partial_update', 'destroy']:
            # To modify/delete, user must be manager or owner for the project
            return [IsAuthenticated(), IsProjectManager()]
        # For list and other actions, IsAuthenticated is sufficient
        # as get_queryset handles specifics for list.
        return super().get_permissions()

    def perform_create(self, serializer):
        # Permission check for creation is handled by get_permissions and IsProjectDeveloperOrHigher
        # We need to ensure the check_object_permissions is called with the project instance
        project = serializer.validated_data['project']
        self.check_object_permissions(self.request, project) # Check against the project
        serializer.save(created_by=self.request.user)

    def get_queryset(self):
        user = self.request.user
        # Start with all configurations or those based on user's project memberships
        if user.is_superuser:
            queryset = ScanConfiguration.objects.all()
        else:
            member_project_ids = ProjectMembership.objects.filter(user=user).values_list('project_id', flat=True)
            # If a non-superuser is not a member of any project, they should see no configurations.
            if not member_project_ids:
                return ScanConfiguration.objects.none()
            queryset = ScanConfiguration.objects.filter(project_id__in=list(member_project_ids))

        # Filter by specific project ID if provided in query parameters
        project_id_query_param = self.request.query_params.get('project', None)
        if project_id_query_param:
            try:
                project_id_to_filter = int(project_id_query_param)
                # If user is not a superuser, ensure they are a member of the project they are trying to filter by.
                # This prevents them from seeing configurations of projects they are not part of, even if they guess a project ID.
                if not user.is_superuser and project_id_to_filter not in member_project_ids:
                    return queryset.none() # Or ScanConfiguration.objects.none() to be more explicit
                
                queryset = queryset.filter(project_id=project_id_to_filter)

            except ValueError:
                # If 'project' query param is not a valid integer, return an empty queryset
                # or consider raising a ValidationError for a 400 response.
                return ScanConfiguration.objects.none() 

        return queryset.select_related('project', 'created_by').distinct()

class UserProfileViewSet(mixins.RetrieveModelMixin,
                         mixins.UpdateModelMixin,
                         viewsets.GenericViewSet):
    """
    Manages the profile for the currently authenticated user.
    Allows retrieving and updating the user's own profile.
    """
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated] # Users manage their own profile

    def get_object(self):
        # Ensure UserProfile exists, which should be guaranteed by signals
        # If it somehow doesn't, this will raise a 404, which is appropriate.
        profile, created = UserProfile.objects.get_or_create(user=self.request.user)
        if created:
            # This case indicates the signal might have failed or is not yet run (e.g. tests)
            # For a GET request, returning the newly created profile is fine.
            pass
        return profile

    def get_queryset(self):
        # Not strictly necessary for get_object, but good practice for GenericViewSet
        return UserProfile.objects.filter(user=self.request.user)

class ApiKeyViewSet(viewsets.ModelViewSet):
    """
    Manages API Keys for the currently authenticated user.
    Allows listing, creating, updating (name, is_active, expires_at), and revoking keys.
    The actual secret key is only shown upon creation.
    """
    serializer_class = ApiKeySerializer
    permission_classes = [IsAuthenticated] # Base for list/create (own keys)

    def get_permissions(self):
        if self.action in ['retrieve', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), CanManageOwnApiKey()]
        # For list, create, and custom 'generate_key_action' IsAuthenticated is sufficient
        # as get_queryset and perform_create/custom action logic handle ownership.
        return super().get_permissions()

    def get_queryset(self):
        # Users can only see and manage their own API keys.
        return ApiKey.objects.filter(user=self.request.user).order_by('-created_at')

    def perform_create(self, serializer):
        # Set the user to the currently authenticated user before saving.
        # The ApiKeySerializer.create method handles the actual key generation and assignment.
        serializer.save(user=self.request.user)

    # The default ModelViewSet provides list, create, retrieve, update, partial_update, destroy.
    # Retrieve will not show the 'key' field due to serializer definition (read_only=True for key, not in model).
    # Update/partial_update can be used to change 'name', 'is_active', 'expires_at'.
    # Destroy will revoke/delete the key.

    # To be absolutely clear that the key is only returned on creation, we could override create response
    # but the serializer setup should handle it by adding the 'key' field to the instance before serialization.
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # perform_create will call serializer.save(user=request.user)
        # which in turn calls the serializer's create method that returns the instance
        # with the temporary 'key' attribute.
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        # The serializer.data will now include the 'key' field because we added it to the instance
        # in ApiKeySerializer.create()
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    @action(detail=False, methods=['post'], url_path='generate')
    def generate_key_action(self, request):
        name = request.data.get('name', '')
        expires_at = request.data.get('expires_at', None)
        
        # Permission check for creating a key is IsAuthenticated (user creates for themselves)
        # If we needed object-level for this custom action (e.g. if it modified an existing key)
        # we would call self.check_object_permissions(request, some_object)

        key_value = secrets.token_urlsafe(32)
        api_key_instance = ApiKey.objects.create(
            user=request.user,
            name=name,
            key=key_value,
            expires_at=expires_at
        )
        # The key_value is what the user needs to copy. It won't be shown again.
        # The instance saved has the key. We return the key_value along with serialized data.
        serialized_data = self.get_serializer(api_key_instance).data
        return Response({"api_key": key_value, "details": serialized_data}, status=status.HTTP_201_CREATED)

# New ViewSet for triggering scans and checking status
class ScanTriggerViewSet(viewsets.ViewSet):
    """
    ViewSet for triggering scans and checking their status.
    Also responsible for creating ScanJob entries.
    """
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['post'], url_path='trigger-sample-scan')
    def trigger_sample_scan(self, request):
        """
        Triggers a sample Bandit scan and creates a ScanJob.
        Expects 'target_info' in the request data (for the sample task).
        Also expects 'project_id' to associate the ScanJob.
        """
        target_info = request.data.get('target_info')
        project_id = request.data.get('project_id')

        if not target_info:
            return Response({"error": "target_info is required for the sample scan task"}, status=status.HTTP_400_BAD_REQUEST)
        if not project_id:
            return Response({"error": "project_id is required to create a ScanJob"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            project = Project.objects.get(pk=project_id)
            # Permission check: User must be Developer or higher for this project.
            # Manually instantiate and check permission
            permission_check = IsProjectDeveloperOrHigher()
            if not permission_check.has_object_permission(request, self, project):
                 return Response({"error": "You do not have permission to trigger scans for this project."}, status=status.HTTP_403_FORBIDDEN)
        except Project.DoesNotExist:
            return Response({"error": f"Project with id {project_id} not found."}, status=status.HTTP_404_NOT_FOUND)

        if not isinstance(target_info, dict) or 'type' not in target_info or 'value' not in target_info:
            return Response({"error": "Invalid target_info structure"}, status=status.HTTP_400_BAD_REQUEST)

        scan_job = ScanJob.objects.create(
            project=project,
            initiator=request.user,
            status=ScanJobStatus.PENDING
        )

        try:
            task = simulate_bandit_scan.delay(target_info=target_info, scan_job_id=scan_job.id)
            scan_job.celery_task_id = task.id
            scan_job.status = ScanJobStatus.QUEUED
            scan_job.save()
            
            serializer = ScanJobSerializer(scan_job)
            return Response(serializer.data, status=status.HTTP_202_ACCEPTED)
        except Exception as e:
            scan_job.status = ScanJobStatus.FAILED
            scan_job.save()
            # Consider logging the full error `e` to a logging system
            return Response({"error": "Failed to submit scan task to Celery", "details": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'], url_path='scan-status/(?P<task_id>[^/.]+)')
    def get_scan_status(self, request, task_id=None):
        """
        Retrieves the status and result of a Celery task, and associated ScanJob details.
        """
        if not task_id:
            return Response({"error": "task_id path parameter is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        task = AsyncResult(task_id)
        # Determine if the task result might contain sensitive information
        # For now, assume results are okay to pass if task is ready.
        # More granular control might be needed based on task types.
        result_data = task.result if task.ready() else None
        status_data = {
            'task_id': task_id,
            'status': task.status,
            'result': result_data,
            'traceback': task.traceback if task.failed() else None
        }

        # Optionally, try to find the ScanJob associated with this celery_task_id
        try:
            scan_job = ScanJob.objects.select_related('project').get(celery_task_id=task_id)
            status_data['scan_job_details'] = ScanJobSerializer(scan_job).data
        except ScanJob.DoesNotExist:
            status_data['scan_job_details'] = 'No ScanJob directly associated with this Celery task ID.'
        except Exception as e: # Catch other potential errors
            status_data['scan_job_details'] = f'Error retrieving ScanJob details: {str(e)}'

        return Response(status_data)

# Modified ScanJobViewSet to allow creation
class ScanJobViewSet(viewsets.ModelViewSet): # Changed from ReadOnlyModelViewSet
    """
    Provides access to ScanJob instances.
    - Create: Users with appropriate project permissions can trigger new scans (create ScanJobs).
    - List/Retrieve: Users can see jobs for projects they are members of.
    - Update/Destroy: Potentially restricted to project managers/owners or superusers.
    """
    serializer_class = ScanJobSerializer
    permission_classes = [IsAuthenticated] # Base permission

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return ScanJob.objects.all().select_related('project', 'scan_configuration', 'initiator').prefetch_related('results')
        
        # Regular users see jobs for projects they are members of
        member_project_ids = ProjectMembership.objects.filter(user=user).values_list('project_id', flat=True)
        if not member_project_ids:
            return ScanJob.objects.none()
        return ScanJob.objects.filter(project_id__in=list(member_project_ids)).select_related(
            'project', 'scan_configuration', 'initiator'
        ).prefetch_related('results')

    def get_permissions(self):
        if self.action == 'create':
            # For creating a ScanJob (triggering a scan), use IsProjectDeveloperOrHigher.
            # This permission class should check against the project specified in the request data.
            return [IsAuthenticated(), IsProjectDeveloperOrHigher()] 
        elif self.action in ['retrieve', 'list']:
            # For list/retrieve, get_queryset already filters by project membership.
            # IsAuthenticated is sufficient here.
            return [IsAuthenticated()]
        elif self.action in ['update', 'partial_update', 'destroy']:
            # For modifying or deleting, restrict to project managers/owners or superuser.
            # This requires object-level permission check based on the ScanJob's project.
            return [IsAuthenticated(), IsProjectManager()] # IsProjectManager needs to handle obj.project
        return super().get_permissions()

    def perform_create(self, serializer):
        project = serializer.validated_data['project']
        user = self.request.user
        scan_configuration = serializer.validated_data['scan_configuration'] # Now required

        # Permission check (simplified, ensure user is member with appropriate role or superuser)
        if not user.is_superuser:
            try:
                membership = ProjectMembership.objects.get(project=project, user=user)
                # Adjusted roles based on ProjectMembership.Role enum, assuming OWNER implies highest privileges like MANAGER
                if membership.role not in [ProjectMembership.Role.DEVELOPER, ProjectMembership.Role.MANAGER]: 
                    raise permissions.PermissionDenied("You do not have permission to trigger scans for this project.")
            except ProjectMembership.DoesNotExist:
                raise permissions.PermissionDenied("You are not a member of this project and cannot trigger scans.")

        # Target info and tool settings are taken directly and exclusively from the selected ScanConfiguration
        job_target_info = scan_configuration.target_details_json
        job_tool_settings = scan_configuration.tool_configurations_json

        # It's crucial that a ScanConfiguration selected for a job has valid targets.
        # This validation should ideally be part of ScanConfiguration model/serializer or a check here.
        if not job_target_info and scan_configuration.has_predefined_targets:
            # This case (config says it has targets, but json is empty) is an inconsistency.
            # For now, we allow it, but the scan task might fail or misbehave.
            # A stricter approach would be to raise a ValidationError here.
            print(f"Warning: ScanConfiguration {scan_configuration.id} has_predefined_targets=True but target_details_json is empty or null.")
        elif not job_target_info and not scan_configuration.has_predefined_targets:
             # This implies the configuration expects targets to be defined elsewhere or not at all (e.g. some tools might not need explicit target files)
             # In our new model, a ScanConfiguration should always have its targets if it's used for a scan.
             # If job_target_info is null here, the scan will likely fail unless the tool itself has a global default.
             # We should enforce that a usable ScanConfiguration has its target_details_json populated.
             # For now, to prevent immediate breakage if has_predefined_targets is false and json is null:
             pass # Let it proceed, but this signals a potentially misconfigured ScanConfiguration

        scan_job = serializer.save(
            initiator=user,
            status=ScanJobStatus.PENDING, # Initial status
            target_info=job_target_info, 
            tool_settings=job_tool_settings
        )
        
        # Trigger the Celery task
        try:
            task = execute_scan_job.delay(scan_job.id)
            scan_job.celery_task_id = task.id
            scan_job.status = ScanJobStatus.QUEUED # Update status to QUEUED
            scan_job.save(update_fields=['celery_task_id', 'status'])
            print(f"Scan job {scan_job.id} submitted to Celery with task ID {task.id}")
        except Exception as e:
            # Handle potential errors during Celery task submission
            print(f"Error submitting scan job {scan_job.id} to Celery: {e}")
            # Optionally, set scan_job status to FAILED here if Celery submission fails critically
            # scan_job.status = ScanJobStatus.FAILED
            # scan_job.save(update_fields=['status'])
            # Depending on requirements, you might want to re-raise the exception or handle it gracefully
            pass # For now, just log and continue, the job remains PENDING if Celery fails

class UserViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Provides a read-only list of users.
    Used for populating user selection fields, e.g., when adding members to a project.
    """
    queryset = User.objects.all().order_by('username')
    serializer_class = UserSimpleSerializer
    permission_classes = [permissions.IsAuthenticated] # Any authenticated user can list users for now

class ProjectMembershipViewSet(viewsets.ModelViewSet):
    """
    Manages project memberships. 
    - List: Members of a project can list memberships for that project.
    - Create, Update, Delete: Only project managers or owners can manage memberships.
    Requires `project_id` query parameter for listing memberships of a specific project.
    """
    queryset = ProjectMembership.objects.all()
    # Default serializer for read actions
    serializer_class = ProjectMembershipSerializer 

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return ProjectMembershipWriteSerializer
        return ProjectMembershipSerializer

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), CanManageProjectMembers()]
        # For list and retrieve, IsAuthenticated is base, get_queryset and object check will further refine.
        # Retrieve will also use CanManageProjectMembers via has_object_permission for the specific membership object.
        return [IsAuthenticated()]

    def get_queryset(self):
        queryset = ProjectMembership.objects.select_related('user', 'project').all()
        project_id = self.request.query_params.get('project_id')
        user = self.request.user

        if not user.is_authenticated:
            return queryset.none()

        if project_id:
            try:
                project = Project.objects.get(pk=project_id)
                # Check if user is at least a viewer of this project to list its members
                if not (user.is_superuser or project.owner == user or 
                        ProjectMembership.objects.filter(project=project, user=user, role__in=[
                            ProjectMembership.Role.VIEWER, 
                            ProjectMembership.Role.DEVELOPER, 
                            ProjectMembership.Role.MANAGER
                        ]).exists()):
                    return queryset.none() # Not a member, cannot list
                return queryset.filter(project_id=project_id)
            except Project.DoesNotExist:
                return queryset.none() # Project not found
        
        # If no project_id, superusers see all, others see none (or memberships for their own projects if desired)
        # For now, require project_id for listing to be specific.
        if user.is_superuser:
             return queryset
        return queryset.none() # Or filter by projects user is member of: ProjectMembership.objects.filter(project__projectmembership__user=user).distinct()

    def perform_create(self, serializer):
        # CanManageProjectMembers in get_permissions already checks if user can manage members for project in request.data
        # The serializer's validate method checks for uniqueness.
        serializer.save()

    def perform_update(self, serializer):
        # CanManageProjectMembers in get_permissions checks via has_object_permission.
        # Serializer validate method prevents changing user/project.
        
        # Business logic: Prevent last manager/owner demotion (simplified check)
        instance = serializer.instance
        new_role = serializer.validated_data.get('role', instance.role)
        project = instance.project

        if instance.role == ProjectMembership.Role.MANAGER and new_role != ProjectMembership.Role.MANAGER:
            # Count other managers for this project
            other_managers_count = ProjectMembership.objects.filter(
                project=project,
                role=ProjectMembership.Role.MANAGER
            ).exclude(pk=instance.pk).count()
            # Check if owner is also a manager (often the case)
            is_owner_manager = project.owner == instance.user # Simplification: owner is this user

            if other_managers_count == 0 and not (project.owner != instance.user and ProjectMembership.objects.filter(project=project, user=project.owner, role=ProjectMembership.Role.MANAGER).exists()):
                if not (project.owner == instance.user and new_role == ProjectMembership.Role.MANAGER): # owner can stay manager
                    raise serializers.ValidationError(
                        "Cannot remove or demote the last manager of the project. Assign another manager first or ensure the project owner has manager rights."
                    )
        serializer.save()

    # perform_destroy default behavior is fine, permissions handle it.

# CI/CD Scan Trigger ViewSet
class CIScanTriggerViewSet(viewsets.ViewSet):
    """
    API endpoint for CI/CD systems to trigger scans.
    Requires API Key authentication.
    """
    authentication_classes = [ApiKeyAuthentication]
    permission_classes = [HasActiveApiKey] # Ensures the key is valid and active
    serializer_class = CIScanTriggerSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            project = serializer.validated_data.get('project')
            scan_configuration = serializer.validated_data.get('scan_configuration')
            commit_hash = serializer.validated_data.get('commit_hash')
            branch_name = serializer.validated_data.get('branch_name')
            repository_url = serializer.validated_data.get('repository_url')
            ci_build_id = serializer.validated_data.get('ci_build_id')

            initiator = request.user 

            scan_job = ScanJob.objects.create(
                project=project,
                scan_configuration=scan_configuration,
                initiator=initiator,
                commit_hash=commit_hash,
                branch_name=branch_name,
                repository_url=repository_url,
                ci_build_id=ci_build_id,
                triggered_by_ci=True,
                status=ScanJobStatus.PENDING 
            )

            # Asynchronously trigger the actual scan execution via Celery
            task = execute_scan_job.delay(scan_job.id)
            
            # Update ScanJob with Celery task ID and set status to QUEUED
            scan_job.celery_task_id = task.id
            scan_job.status = ScanJobStatus.QUEUED
            scan_job.save(update_fields=['celery_task_id', 'status'])

            response_serializer = ScanJobSerializer(scan_job)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# Docker API Views
class ListDockerContainersView(APIView):
    """
    Lists all currently running Docker containers.
    Requires admin privileges.
    """
    permission_classes = [IsAdminUser]

    def get(self, request, *args, **kwargs):
        containers_or_error = list_running_containers()
        if isinstance(containers_or_error, str): # Error message returned
            if "No running containers found" in containers_or_error:
                 return Response({"message": containers_or_error}, status=status.HTTP_200_OK) # Or 404 if preferred
            return Response({"error": containers_or_error}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response(containers_or_error, status=status.HTTP_200_OK)

class GetDockerContainerPathsView(APIView):
    """
    Retrieves potential host code paths for a given Docker container.
    Requires admin privileges.
    """
    permission_classes = [IsAdminUser]

    def get(self, request, container_id, *args, **kwargs):
        paths_or_error = get_container_code_paths(container_id)
        if isinstance(paths_or_error, str): # Error message returned
            if "not found" in paths_or_error.lower():
                return Response({"error": paths_or_error}, status=status.HTTP_404_NOT_FOUND)
            # For other errors from the service, consider them server-side issues or specific Docker issues
            return Response({"error": paths_or_error}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        if not paths_or_error: # Empty list, but valid response
            return Response([], status=status.HTTP_200_OK)
        return Response(paths_or_error, status=status.HTTP_200_OK)

class ListDockerComposeProjectsView(APIView):
    """
    Lists Docker containers grouped by their 'com.docker.compose.project' label.
    Requires admin privileges.
    """
    permission_classes = [IsAdminUser]

    def get(self, request, *args, **kwargs):
        grouped_projects_or_error = get_grouped_docker_compose_projects()
        if isinstance(grouped_projects_or_error, str): # Error message returned from service
            return Response({"error": grouped_projects_or_error}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # Transform the dictionary into a list of objects for a more common API response structure
        # e.g., [{"project_name": "my_project", "containers": [...]}, ...]
        response_data = []
        for project_name, containers in grouped_projects_or_error.items():
            response_data.append({
                "compose_project_name": project_name,
                "containers": containers
            })

        return Response(response_data, status=status.HTTP_200_OK)
