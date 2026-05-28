"""
tasks/views.py

TaskViewSet with scope-filtered list, full CRUD,
and two custom actions: assign and update_status.

Access control:
  - All roles with can_read on tasks → list/retrieve (scope filtered)
  - Admin / RM / TL (can_create) → create
  - Admin / RM / TL (can_update) → assign, update_status, partial_update
  - Admin only (can_delete) → destroy (soft: sets cancelled)
  - Field Agent → can only update_status on own tasks (pending → in_progress)
  - Auditor → read-only
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from tasks.models import Task
from tasks.serializers import (
    TaskListSerializer,
    TaskDetailSerializer,
    TaskCreateSerializer,
    TaskAssignSerializer,
    TaskStatusSerializer,
)
from tasks.filters import TaskFilter
from tasks.mixins import ScopedQuerysetMixin
from accounts.permissions import HasModulePermission, IsAdminRole


class TaskViewSet(ScopedQuerysetMixin, viewsets.ModelViewSet):
    """
    /api/tasks/
    Scope-filtered task management.
    """
    module = 'tasks'
    queryset = Task.objects.select_related(
        'created_by', 'assigned_to',
        'region', 'team',
        'created_by__role', 'assigned_to__role',
    ).all()

    filterset_class = TaskFilter
    search_fields = ['title', 'description']
    ordering_fields = ['created_at', 'updated_at', 'due_date', 'priority', 'status']
    ordering = ['-created_at']

    # ── Serializer routing ────────────────────────────────────

    def get_serializer_class(self):
        if self.action == 'list':
            return TaskListSerializer
        if self.action == 'create':
            return TaskCreateSerializer
        if self.action == 'assign':
            return TaskAssignSerializer
        if self.action == 'update_status':
            return TaskStatusSerializer
        return TaskDetailSerializer

    # ── Permission routing ────────────────────────────────────

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [IsAuthenticated(), HasModulePermission()]
        if self.action == 'create':
            return [IsAuthenticated(), HasModulePermission()]
        if self.action in ['partial_update', 'update', 'assign', 'update_status']:
            return [IsAuthenticated(), HasModulePermission()]
        if self.action == 'destroy':
            return [IsAuthenticated(), IsAdminRole()]
        return [IsAuthenticated()]

    # ── CREATE ────────────────────────────────────────────────

    def create(self, request, *args, **kwargs):
        serializer = TaskCreateSerializer(
            data=request.data,
            context={'request': request},
        )
        serializer.is_valid(raise_exception=True)
        task = serializer.save()

        # Activity log
        _log(request.user, 'task_created', task, {
            'title': task.title,
            'priority': task.priority,
            'region': str(task.region) if task.region else None,
            'team': str(task.team) if task.team else None,
        })

        return Response(
            TaskDetailSerializer(task).data,
            status=status.HTTP_201_CREATED,
        )

    # ── DESTROY (soft — Admin only) ────────────────────────────

    def destroy(self, request, *args, **kwargs):
        task = self.get_object()
        if task.status == Task.STATUS_COMPLETED:
            return Response(
                {
                    'error': True,
                    'code': 'INVALID_STATE',
                    'message': 'Completed tasks cannot be deleted.',
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        task.status = Task.STATUS_CANCELLED
        task.save(update_fields=['status', 'updated_at'])

        _log(request.user, 'task_deleted', task, {'title': task.title})

        return Response(
            {'message': f'Task "{task.title}" has been cancelled and archived.'},
            status=status.HTTP_200_OK,
        )

    # ── CUSTOM ACTION: assign ─────────────────────────────────

    @action(detail=True, methods=['post'], url_path='assign')
    def assign(self, request, pk=None):
        """
        POST /api/tasks/{id}/assign/
        Body: { "assigned_to_id": "<uuid>" }
        Assigns the task to a Field Agent within the caller's scope.
        """
        task = self.get_object()

        # Cancelled or completed tasks cannot be reassigned
        if task.status in [Task.STATUS_COMPLETED, Task.STATUS_CANCELLED]:
            return Response(
                {
                    'error': True,
                    'code': 'INVALID_STATE',
                    'message': f'Cannot assign a task that is "{task.status}".',
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = TaskAssignSerializer(
            data=request.data,
            context={'request': request},
        )
        serializer.is_valid(raise_exception=True)

        agent = serializer.validated_data['assigned_to_id']
        previous_assignee = task.assigned_to

        task.assigned_to = agent
        
        if agent.region:
            task.region = agent.region
        if agent.team:
            task.team = agent.team

        task.save(update_fields=['assigned_to', 'region', 'team', 'updated_at'])

        _log(request.user, 'task_assigned', task, {
            'assigned_to': agent.email,
            'previous_assignee': previous_assignee.email if previous_assignee else None,
        })

        return Response(TaskDetailSerializer(task).data, status=status.HTTP_200_OK)

    # ── CUSTOM ACTION: update_status ──────────────────────────

    @action(detail=True, methods=['patch'], url_path='status')
    def update_status(self, request, pk=None):
        """
        PATCH /api/tasks/{id}/status/
        Body: { "status": "in_progress" }
        Validates the transition is allowed before saving.
        """
        task = self.get_object()

        # Field Agents can only update their OWN tasks
        user = request.user
        if user.role and user.role.name == 'Field Agent':
            if task.assigned_to != user:
                return Response(
                    {
                        'error': True,
                        'code': 'PERMISSION_DENIED',
                        'message': 'You can only update the status of tasks assigned to you.',
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

        serializer = TaskStatusSerializer(
            data=request.data,
            context={'task': task, 'request': request},
        )
        serializer.is_valid(raise_exception=True)

        old_status = task.status
        task.status = serializer.validated_data['status']
        task.save(update_fields=['status', 'updated_at'])

        _log(request.user, 'task_status_changed', task, {
            'old_status': old_status,
            'new_status': task.status,
        })

        return Response(TaskDetailSerializer(task).data, status=status.HTTP_200_OK)


# ─────────────────────────────────────────────────────────────
# Logging helper (graceful — never crashes the request)
# ─────────────────────────────────────────────────────────────

def _log(actor, action, task, metadata=None):
    try:
        from logs.utils import log_activity
        log_activity(actor, action, task, metadata)
    except Exception:
        pass
