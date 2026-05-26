"""
accounts/permissions.py

Custom DRF permission classes used across all apps.
These are the two core building blocks of the entire access control system.
"""

from rest_framework.permissions import BasePermission
from accounts.models import ModulePermission


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────

def _get_module_permission(user, module):
    """
    Fetch the ModulePermission row for this user's role and module.
    Returns None if the user has no role or no permission row exists.
    """
    if not user or not user.is_authenticated or not user.role:
        return None
    try:
        return ModulePermission.objects.select_related('role').get(
            role=user.role,
            module=module,
        )
    except ModulePermission.DoesNotExist:
        return None


def _http_method_to_action(method):
    """Map HTTP method to the corresponding can_* field name."""
    return {
        'GET': 'can_read',
        'HEAD': 'can_read',
        'OPTIONS': 'can_read',
        'POST': 'can_create',
        'PUT': 'can_update',
        'PATCH': 'can_update',
        'DELETE': 'can_delete',
    }.get(method.upper(), 'can_read')


# ─────────────────────────────────────────────────────────────
# HasModulePermission
# ─────────────────────────────────────────────────────────────

class HasModulePermission(BasePermission):
    """
    View-level permission.

    The view must define `module = 'tasks'` (or any MODULE_* constant).
    This class looks up the ModulePermission row for the user's role
    and checks the relevant can_* flag for the HTTP method.

    Usage:
        class TaskViewSet(ModelViewSet):
            module = 'tasks'
            permission_classes = [IsAuthenticated, HasModulePermission]
    """

    message = 'You do not have permission to perform this action on this module.'

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        module = getattr(view, 'module', None)
        if not module:
            # If no module is declared on the view, allow (fallback)
            return True

        perm = _get_module_permission(request.user, module)
        if not perm:
            return False

        action_field = _http_method_to_action(request.method)
        return getattr(perm, action_field, False)


# ─────────────────────────────────────────────────────────────
# IsOwnerOrInScope
# ─────────────────────────────────────────────────────────────

class IsOwnerOrInScope(BasePermission):
    """
    Object-level permission.

    Called by get_object() → check_object_permissions().
    Validates that the requesting user's scope covers this specific object.

    Scope rules:
      all    → always pass
      region → obj.region must match user.region
      team   → obj.team must match user.team
      own    → obj must be owned by this user (checks assigned_to or agent field)

    The view must define `module` for scope lookup to work.
    """

    message = 'You do not have scope access to this record.'

    def has_object_permission(self, request, view, obj):
        user = request.user
        module = getattr(view, 'module', None)

        if not module:
            return True

        perm = _get_module_permission(user, module)
        if not perm:
            return False

        scope = perm.scope

        if scope == ModulePermission.SCOPE_ALL:
            return True

        if scope == ModulePermission.SCOPE_REGION:
            obj_region = getattr(obj, 'region', None)
            return obj_region is not None and obj_region == user.region

        if scope == ModulePermission.SCOPE_TEAM:
            obj_team = getattr(obj, 'team', None)
            return obj_team is not None and obj_team == user.team

        if scope == ModulePermission.SCOPE_OWN:
            # Tasks: check assigned_to
            assigned_to = getattr(obj, 'assigned_to', None)
            if assigned_to is not None:
                return assigned_to == user
            # Visits: check agent
            agent = getattr(obj, 'agent', None)
            if agent is not None:
                return agent == user
            # Fallback: created_by
            created_by = getattr(obj, 'created_by', None)
            if created_by is not None:
                return created_by == user
            return False

        return False


# ─────────────────────────────────────────────────────────────
# IsAdminRole
# ─────────────────────────────────────────────────────────────

class IsAdminRole(BasePermission):
    """
    Shortcut permission — only allows Admin role.
    Used for user management endpoints and task deletion.
    """
    message = 'Only Admin users can perform this action.'

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role is not None
            and request.user.role.name == 'Admin'
        )


# ─────────────────────────────────────────────────────────────
# IsReadOnly
# ─────────────────────────────────────────────────────────────

class IsReadOnly(BasePermission):
    """
    Allows only safe (read) HTTP methods.
    Used for Auditor role enforcement at the view level.
    """
    SAFE_METHODS = ('GET', 'HEAD', 'OPTIONS')

    message = 'This resource is read-only for your role.'

    def has_permission(self, request, view):
        return request.method in self.SAFE_METHODS
