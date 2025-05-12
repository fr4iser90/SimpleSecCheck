from rest_framework import permissions
from .models import ProjectMembership, Project

# Role constants are no longer needed here as permissions directly use ProjectMembership.Role enum.

class IsSuperUser(permissions.BasePermission):
    """Allows access only to superusers."""
    def has_permission(self, request, view):
        return request.user and request.user.is_superuser

class IsProjectOwner(permissions.BasePermission):
    """Allows access only to the project owner.
       Assumes the object being checked (`obj`) has an `owner` attribute.
    """
    def has_object_permission(self, request, view, obj):
        return obj.owner == request.user

class IsProjectManager(permissions.BasePermission):
    """Allows access if the user is a superuser, project owner, or has 'manager' role in ProjectMembership.
       Assumes `obj` is a Project instance or has a `project` attribute linking to one.
    """
    def has_object_permission(self, request, view, obj):
        # Determine the project instance from the object being checked
        project = None
        if hasattr(obj, 'owner') and hasattr(obj, 'members'): # obj is likely a Project instance
            project = obj
        elif hasattr(obj, 'project'): # obj has a foreign key to Project (e.g., ScanConfiguration, ScanJob)
            project = obj.project
        
        if not project:
            return False # Cannot determine project context

        if request.user.is_superuser or project.owner == request.user:
            return True
        return ProjectMembership.objects.filter(
            project=project,
            user=request.user,
            role=ProjectMembership.Role.MANAGER
        ).exists()

class IsProjectDeveloperOrHigher(permissions.BasePermission):
    """Allows access if user is superuser, owner, or has 'developer' or 'manager' role.
       Assumes `obj` is a Project instance or has a `project` attribute linking to one.
    """
    def has_object_permission(self, request, view, obj):
        project = None
        if hasattr(obj, 'owner') and hasattr(obj, 'members'):
            project = obj
        elif hasattr(obj, 'project'):
            project = obj.project
        
        if not project:
            return False

        if request.user.is_superuser or project.owner == request.user:
            return True
        return ProjectMembership.objects.filter(
            project=project,
            user=request.user,
            role__in=[ProjectMembership.Role.MANAGER, ProjectMembership.Role.DEVELOPER]
        ).exists()

class IsProjectViewerOrHigher(permissions.BasePermission):
    """Allows access if user is superuser, owner, or has 'viewer', 'developer', or 'manager' role.
       Assumes `obj` is a Project instance or has a `project` attribute linking to one.
    """
    def has_object_permission(self, request, view, obj):
        project = None
        if hasattr(obj, 'owner') and hasattr(obj, 'members'):
            project = obj
        elif hasattr(obj, 'project'):
            project = obj.project
            
        if not project:
            return False

        if request.user.is_superuser or project.owner == request.user:
            return True
        return ProjectMembership.objects.filter(
            project=project,
            user=request.user,
            role__in=[ProjectMembership.Role.MANAGER, ProjectMembership.Role.DEVELOPER, ProjectMembership.Role.VIEWER]
        ).exists()

class CanManageOwnApiKey(permissions.BasePermission):
    """User can manage their own API key (retrieve, update name/expiry, delete).
       Superusers can also manage any API key.
       Assumes `obj` is an ApiKey instance.
    """
    def has_object_permission(self, request, view, obj):
        return obj.user == request.user or request.user.is_superuser

# General permission for authenticated users - can be used as a base if needed,
# but specific classes above are preferred for clarity.
class IsAuthenticatedAndHasAccessToProject(permissions.IsAuthenticated):
    """Checks if user is authenticated and has any role in the project or is the owner.
       Assumes `obj` is a Project instance or has a `project` attribute linking to one.
       Primarily for cases where any project membership (even just viewer) is enough for a base check,
       and queryset filtering is the main guard for lists.
    """
    def has_object_permission(self, request, view, obj):
        project = None
        if hasattr(obj, 'owner') and hasattr(obj, 'members'): 
            project = obj
        elif hasattr(obj, 'project'):
            project = obj.project
        else:
            return False 
        
        if not project:
             return False

        if request.user.is_superuser or project.owner == request.user:
            return True
        return ProjectMembership.objects.filter(project=project, user=request.user).exists()

class CanManageProjectMembers(permissions.BasePermission):
    """
    Allows access only to users who are managers or owners of the project
    associated with the ProjectMembership object or a given Project instance.
    """

    def has_permission(self, request, view):
        # For list views, this might be too restrictive or need project context.
        # For 'create', we need to check against the project being assigned to.
        if view.action == 'create':
            project_id = request.data.get('project')
            if not project_id:
                # If project_id is taken from URL (e.g. nested routes), this check might differ.
                return False # Project context is required to check permission.
            try:
                project = Project.objects.get(pk=project_id)
                return self._is_manager_or_owner(request.user, project)
            except Project.DoesNotExist:
                return False # Project not found, deny permission.
        # For other actions like list, default to IsAuthenticated if it's a top-level list,
        # or let get_queryset handle filtering by project.
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        # obj is expected to be a ProjectMembership instance
        if isinstance(obj, ProjectMembership):
            project = obj.project
        elif isinstance(obj, Project): # If checking against a Project directly
            project = obj
        else:
            return False # Not a ProjectMembership or Project instance
        
        return self._is_manager_or_owner(request.user, project)

    def _is_manager_or_owner(self, user, project):
        if not user or not project:
            return False
        if user.is_superuser or project.owner == user:
            return True
        return ProjectMembership.objects.filter(
            project=project,
            user=user,
            role=ProjectMembership.Role.MANAGER
        ).exists()

# Notes on usage:
# - These permissions primarily implement `has_object_permission`.
# - For list views (get_queryset), filtering should be done within the ViewSet's `get_queryset` method.
# - For `create` actions, `has_permission` might be needed on the permission class if it's a general check,
#   or `check_permissions` / `check_object_permissions` can be called manually in `perform_create` or `create` method
#   if the check depends on incoming data (like a `project_id`).
# - `IsProjectOwner` specifically checks `obj.owner == request.user`.
# - Other project-related permissions (`IsProjectManager`, `IsProjectDeveloperOrHigher`, `IsProjectViewerOrHigher`)
#   dynamically determine the project from `obj` (if `obj` is Project itself or has a `obj.project` attribute)
#   and then check ownership or `ProjectMembership` roles.

# Example of how these might be used in a viewset:
# from .permissions import IsAdmin, IsProjectOwner
# class SomeViewSet(viewsets.ModelViewSet):
#     permission_classes = [permissions.IsAuthenticated, IsAdmin | IsProjectOwner] # OR logic
#     # For object-level with IsProjectOwner:
#     # permission_classes = [permissions.IsAuthenticated, IsProjectOwner]

# Note: The actual creation and assignment of Groups (Administrator, Project Owner, etc.)
# to users would need to be handled, e.g., via Django admin, signals, or a management command. 

# Make sure ROLE_PROJECT_OWNER is defined if used in views.py, or rely on is_staff / is_superuser
# For simplicity, we will rely on is_superuser for admin-like full access powers in most permissions.
# ROLE_PROJECT_OWNER was used in some older permission snippets but new ones focus on ProjectMembership roles. 

class HasActiveApiKey(permissions.BasePermission):
    """
    Allows access if a valid and active API key is provided in the request.
    Assumes an authentication backend populates `request.auth` with the ApiKey instance.
    """
    message = "Invalid or inactive API key."

    def has_permission(self, request, view):
        # request.auth should be the ApiKey instance if a custom API key auth backend is used
        if not request.auth or not isinstance(request.auth, ApiKey):
            return False
        return request.auth.is_active

# ROLE_PROJECT_OWNER was used in some older permission snippets but new ones focus on ProjectMembership roles. 