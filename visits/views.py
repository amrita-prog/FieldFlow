"""
visits/views.py

VisitViewSet — complete visit lifecycle management.

Custom actions:
  POST   /api/visits/{id}/start/      → scheduled → in_progress
  POST   /api/visits/{id}/complete/   → in_progress → completed
  PATCH  /api/visits/{id}/notes/      → update notes, triggers MockAIService
  GET    /api/visits/{id}/ai-output/  → fetch AI output for this visit

Scope:
  Uses ScopedQuerysetMixin with scope_fields overridden to 'agent'
  instead of 'assigned_to' (which is the Task convention).

Access:
  - Field Agent → own visits only (scope=own, own_user_field='agent')
  - Team Lead   → team visits
  - Regional Mgr→ region visits
  - Admin       → all visits
  - Auditor     → all visits (read-only enforced by ModulePermission)
"""

from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from visits.models import Visit, AIOutput
from visits.serializers import (
    VisitListSerializer,
    VisitDetailSerializer,
    VisitCreateSerializer,
    VisitNotesSerializer,
    VisitCompleteSerializer,
    AIOutputSerializer,
)
from visits.filters import VisitFilter
from tasks.mixins import ScopedQuerysetMixin
from accounts.permissions import HasModulePermission


class VisitViewSet(ScopedQuerysetMixin, viewsets.ModelViewSet):
    """
    /api/visits/
    Full visit lifecycle with Mock AI integration.
    """
    module = 'visits'

    # Override scope field — visits use 'agent' not 'assigned_to'
    scope_fields = {
        'own_user_field': 'agent',
        'team_field': 'agent__team',
        'region_field': 'agent__region',
    }

    queryset = Visit.objects.select_related(
        'task', 'agent', 'agent__role',
        'agent__team', 'agent__region',
        'ai_output',
    ).all()

    filterset_class = VisitFilter
    search_fields = ['location', 'notes']
    ordering_fields = ['created_at', 'started_at', 'completed_at', 'status']
    ordering = ['-created_at']

    http_method_names = ['get', 'post', 'patch', 'delete', 'head', 'options']

    # ── Serializer routing ────────────────────────────────────

    def get_serializer_class(self):
        if self.action == 'list':
            return VisitListSerializer
        if self.action == 'create':
            return VisitCreateSerializer
        if self.action == 'add_notes':
            return VisitNotesSerializer
        if self.action == 'complete':
            return VisitCompleteSerializer
        if self.action == 'ai_output':
            return AIOutputSerializer
        return VisitDetailSerializer

    # ── Permission routing ────────────────────────────────────

    def get_permissions(self):
        return [IsAuthenticated(), HasModulePermission()]

    # ── CREATE ────────────────────────────────────────────────

    def create(self, request, *args, **kwargs):
        serializer = VisitCreateSerializer(
            data=request.data,
            context={'request': request},
        )
        serializer.is_valid(raise_exception=True)
        visit = serializer.save()

        _log(request.user, 'visit_created', visit, {
            'location': visit.location,
            'agent': visit.agent.email,
            'task_id': str(visit.task_id) if visit.task_id else None,
        })

        return Response(
            VisitDetailSerializer(visit).data,
            status=status.HTTP_201_CREATED,
        )

    # ── Disable full update (PUT) — use PATCH only ────────────

    def update(self, request, *args, **kwargs):
        return Response(
            {'error': True, 'code': 'METHOD_NOT_ALLOWED',
             'message': 'Use PATCH /notes/ to update visit notes.'},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    # ── CUSTOM ACTION: start ──────────────────────────────────

    @action(detail=True, methods=['post'], url_path='start')
    def start(self, request, pk=None):
        """
        POST /api/visits/{id}/start/
        Marks visit as in_progress. Only the assigned agent can do this.
        Visit must be in 'scheduled' state.
        """
        # Use unscoped lookup so supervisors/admins get 403 (not 404)
        # for visits outside their team, and agents get 403 for others' visits
        visit = _get_visit_or_404(pk)
        if visit is None:
            from rest_framework.exceptions import NotFound
            raise NotFound()

        # Only the assigned agent or Admin can start a visit
        if not _can_modify_visit(request.user, visit):
            return Response(
                {
                    'error': True,
                    'code': 'PERMISSION_DENIED',
                    'message': 'You can only start visits assigned to you.',
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        if not visit.can_transition_to(Visit.STATUS_IN_PROGRESS):
            return Response(
                {
                    'error': True,
                    'code': 'INVALID_STATE',
                    'message': (
                        f'Visit is currently "{visit.status}". '
                        f'Only scheduled visits can be started.'
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        visit.status = Visit.STATUS_IN_PROGRESS
        visit.started_at = timezone.now()
        visit.save(update_fields=['status', 'started_at', 'updated_at'])

        _log(request.user, 'visit_started', visit, {
            'location': visit.location,
            'started_at': visit.started_at.isoformat(),
        })

        return Response(VisitDetailSerializer(visit).data, status=status.HTTP_200_OK)

    # ── CUSTOM ACTION: complete ───────────────────────────────

    @action(detail=True, methods=['post'], url_path='complete')
    def complete(self, request, pk=None):
        """
        POST /api/visits/{id}/complete/
        Body: { "outcome": "successful" | "failed" | "partial" }
        Marks visit as completed. Must be in_progress first.
        """
        visit = _get_visit_or_404(pk)
        if visit is None:
            from rest_framework.exceptions import NotFound
            raise NotFound()

        if not _can_modify_visit(request.user, visit):
            return Response(
                {
                    'error': True,
                    'code': 'PERMISSION_DENIED',
                    'message': 'You can only complete visits assigned to you.',
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        if not visit.can_transition_to(Visit.STATUS_COMPLETED):
            return Response(
                {
                    'error': True,
                    'code': 'INVALID_STATE',
                    'message': (
                        f'Visit is currently "{visit.status}". '
                        f'Only in-progress visits can be completed.'
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = VisitCompleteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        visit.status = Visit.STATUS_COMPLETED
        visit.completed_at = timezone.now()
        visit.outcome = serializer.validated_data['outcome']
        visit.save(update_fields=['status', 'completed_at', 'outcome', 'updated_at'])

        _log(request.user, 'visit_completed', visit, {
            'outcome': visit.outcome,
            'completed_at': visit.completed_at.isoformat(),
        })

        return Response(VisitDetailSerializer(visit).data, status=status.HTTP_200_OK)

    # ── CUSTOM ACTION: add_notes ──────────────────────────────

    @action(detail=True, methods=['patch'], url_path='notes')
    def add_notes(self, request, pk=None):
        """
        PATCH /api/visits/{id}/notes/
        Body: { "notes": "...", "outcome": "partial" (optional) }

        Updates visit notes and triggers MockAIService.
        AI output is saved to AIOutput and returned in the response.
        """
        visit = _get_visit_or_404(pk)
        if visit is None:
            from rest_framework.exceptions import NotFound
            raise NotFound()

        if not _can_modify_visit(request.user, visit):
            return Response(
                {
                    'error': True,
                    'code': 'PERMISSION_DENIED',
                    'message': 'You can only update notes for your own visits.',
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        if visit.status == Visit.STATUS_CANCELLED:
            return Response(
                {
                    'error': True,
                    'code': 'INVALID_STATE',
                    'message': 'Cannot add notes to a cancelled visit.',
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = VisitNotesSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Save notes and optional outcome
        visit.notes = serializer.validated_data['notes']
        if 'outcome' in serializer.validated_data:
            visit.outcome = serializer.validated_data['outcome']
        visit.save(update_fields=['notes', 'outcome', 'updated_at'])

        # ── Generate AI output ────────────────────────────────
        ai_data = _generate_ai_output(visit)

        _log(request.user, 'visit_notes_added', visit, {
            'notes_length': len(visit.notes),
            'ai_risk_flag': ai_data.get('risk_flag'),
        })
        _log(request.user, 'ai_output_generated', visit, {
            'risk_flag': ai_data.get('risk_flag'),
            'follow_up': ai_data.get('follow_up'),
        })

        return Response(VisitDetailSerializer(visit).data, status=status.HTTP_200_OK)

    # ── CUSTOM ACTION: ai_output ──────────────────────────────

    @action(detail=True, methods=['get'], url_path='ai-output')
    def ai_output(self, request, pk=None):
        """
        GET /api/visits/{id}/ai-output/
        Returns the stored AI output for this visit, or 404 if none yet.
        """
        visit = _get_visit_or_404(pk)
        if visit is None:
            from rest_framework.exceptions import NotFound
            raise NotFound()
        try:
            output = visit.ai_output
        except AIOutput.DoesNotExist:
            return Response(
                {
                    'error': True,
                    'code': 'NOT_FOUND',
                    'message': 'No AI output found. Submit visit notes first.',
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(AIOutputSerializer(output).data, status=status.HTTP_200_OK)


# ─────────────────────────────────────────────────────────────
# Private helpers
# ─────────────────────────────────────────────────────────────

def _can_modify_visit(user, visit):
    """
    Field Agent → only their own visits.
    Admin, RM, TL → any visit in their scope.
    """
    if not user.role:
        return False
    if user.role.name == 'Admin':
        return True
    if user.role.name == 'Field Agent':
        return visit.agent == user
    # RM and TL can start/complete visits in their scope
    return True


def _generate_ai_output(visit) -> dict:
    """
    Calls MockAIService and saves/updates the AIOutput record.
    Returns the AI data dict.
    """
    from ai_service.service import MockAIService
    service = MockAIService()
    ai_data = service.generate_output(notes=visit.notes, visit=visit)

    AIOutput.objects.update_or_create(
        visit=visit,
        defaults={
            'summary': ai_data['summary'],
            'follow_up': ai_data['follow_up'],
            'risk_flag': ai_data['risk_flag'],
        },
    )
    return ai_data


def _log(actor, action, visit, metadata=None):
    try:
        from logs.utils import log_activity
        log_activity(actor, action, visit, metadata)
    except Exception:
        pass


def _get_visit_or_404(pk):
    """
    Fetch a visit by PK without scope filtering.
    Used in custom actions so we can return proper 403 instead of 404
    when a field agent tries to access another agent's visit.
    Returns None if the visit does not exist (caller raises NotFound).
    """
    try:
        return Visit.objects.select_related(
            'task', 'agent', 'agent__role',
            'agent__team', 'agent__region',
            'ai_output',
        ).get(pk=pk)
    except Visit.DoesNotExist:
        return None
