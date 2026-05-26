"""
tasks/mixins.py

ScopedQuerysetMixin — reusable mixin for all ViewSets that need
scope-based queryset filtering (tasks, visits, logs).

How it works:
  1. Reads the user's role from request.user.role
  2. Looks up their ModulePermission.scope for the view's `module`
  3. Applies the correct filter to the base queryset

Scope rules:
  all    → no filter applied (Admin, Auditor)
  region → filter by user's region
  team   → filter by user's team
  own    → filter by assigned_to=user (tasks) or agent=user (visits)

Views that use this mixin must define:
  module = 'tasks'   (or 'visits', 'logs', etc.)
  scope_fields = {   (optional override of default field names)
      'own': 'assigned_to',
      'team': 'team',
      'region': 'region',
  }
"""

from accounts.models import ModulePermission


class ScopedQuerysetMixin:
    """
    Include this mixin in a ViewSet to automatically scope
    its queryset to the requesting user's allowed data range.
    """

    # Default field names on the model for each scope level.
    # Subclasses can override if the field names differ.
    scope_fields = {
        'own_user_field': 'assigned_to',   # overridden to 'agent' in VisitViewSet
        'team_field': 'team',
        'region_field': 'region',
    }

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user

        if not user.is_authenticated or not user.role:
            return qs.none()

        module = getattr(self, 'module', None)
        if not module:
            return qs

        # Fetch scope from DB
        try:
            perm = ModulePermission.objects.get(role=user.role, module=module)
            scope = perm.scope
        except ModulePermission.DoesNotExist:
            return qs.none()

        # Apply the appropriate filter
        if scope == ModulePermission.SCOPE_ALL:
            return qs

        if scope == ModulePermission.SCOPE_REGION:
            region_field = self.scope_fields.get('region_field', 'region')
            if user.region:
                return qs.filter(**{region_field: user.region})
            return qs.none()

        if scope == ModulePermission.SCOPE_TEAM:
            team_field = self.scope_fields.get('team_field', 'team')
            if user.team:
                return qs.filter(**{team_field: user.team})
            return qs.none()

        if scope == ModulePermission.SCOPE_OWN:
            own_field = self.scope_fields.get('own_user_field', 'assigned_to')
            return qs.filter(**{own_field: user})

        return qs.none()
