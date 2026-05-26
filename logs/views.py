"""
logs/views.py

ActivityLogViewSet — read-only, scoped, filterable.

Scope rules:
  Admin    → all logs
  Auditor  → all logs (read-only)
  RM       → logs where actor is in their region
  TL       → logs where actor is in their team
  FA       → 403

Filters:
  ?action=task_assigned
  ?actor_id=<uuid>
  ?target_type=task
  ?from=2025-01-01
  ?to=2025-12-31
"""

from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from logs.models import ActivityLog
from logs.serializers import ActivityLogSerializer


class ActivityLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    GET /api/logs/          → list (scoped + filtered)
    GET /api/logs/{id}/     → single log entry
    """
    serializer_class = ActivityLogSerializer
    ordering = ['-timestamp']
    ordering_fields = ['timestamp', 'action']

    def get_permissions(self):
        return [IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        role_name = user.role.name if user.role else None

        # Field Agents and unauthenticated users → no access
        if role_name == 'Field Agent' or role_name is None:
            return ActivityLog.objects.none()

        qs = ActivityLog.objects.select_related(
            'actor', 'actor__role', 'actor__region', 'actor__team'
        ).all()

        # Scope by role
        if role_name == 'Regional Manager' and user.region:
            qs = qs.filter(actor__region=user.region)
        elif role_name == 'Team Lead' and user.team:
            qs = qs.filter(actor__team=user.team)
        # Admin and Auditor → full queryset (no filter)

        # ── Apply query param filters ─────────────────────────
        params = self.request.query_params

        action = params.get('action')
        if action:
            qs = qs.filter(action=action)

        actor_id = params.get('actor_id')
        if actor_id:
            qs = qs.filter(actor__id=actor_id)

        target_type = params.get('target_type')
        if target_type:
            qs = qs.filter(target_type=target_type.lower())

        from_date = params.get('from')
        if from_date:
            qs = qs.filter(timestamp__date__gte=from_date)

        to_date = params.get('to')
        if to_date:
            qs = qs.filter(timestamp__date__lte=to_date)

        return qs.order_by('-timestamp')

    def list(self, request, *args, **kwargs):
        user = request.user
        role_name = user.role.name if user.role else None

        if role_name == 'Field Agent' or role_name is None:
            return Response(
                {
                    'error': True,
                    'code': 'PERMISSION_DENIED',
                    'message': 'Field Agents do not have access to activity logs.',
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().list(request, *args, **kwargs)
