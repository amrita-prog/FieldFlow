"""
logs/models.py

ActivityLog — immutable audit trail for all significant system events.
"""

import uuid
from django.db import models
from accounts.models import User


class ActivityLog(models.Model):

    class ActionTypes(models.TextChoices):
        # Auth
        USER_LOGGED_IN   = 'user_logged_in',   'User Logged In'
        USER_LOGGED_OUT  = 'user_logged_out',   'User Logged Out'

        # Tasks
        TASK_CREATED        = 'task_created',        'Task Created'
        TASK_ASSIGNED       = 'task_assigned',        'Task Assigned'
        TASK_STATUS_CHANGED = 'task_status_changed',  'Task Status Changed'
        TASK_DELETED        = 'task_deleted',          'Task Deleted'

        # Visits
        VISIT_CREATED      = 'visit_created',       'Visit Created'
        VISIT_STARTED      = 'visit_started',        'Visit Started'
        VISIT_NOTES_ADDED  = 'visit_notes_added',    'Visit Notes Added'
        VISIT_COMPLETED    = 'visit_completed',      'Visit Completed'
        VISIT_CANCELLED    = 'visit_cancelled',      'Visit Cancelled'

        # AI
        AI_OUTPUT_GENERATED = 'ai_output_generated', 'AI Output Generated'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    actor = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='activity_logs',
    )

    action = models.CharField(
        max_length=50,
        choices=ActionTypes.choices,
        db_index=True,
    )

    # Stores the class name of the target object (e.g. 'task', 'visit')
    target_type = models.CharField(max_length=50, blank=True)

    # Stores the UUID of the target object as a string
    target_id = models.CharField(max_length=36, blank=True)

    # Flexible JSONB-style storage for extra context
    metadata = models.JSONField(default=dict, blank=True)

    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        actor_str = self.actor.email if self.actor else 'system'
        return f"[{self.timestamp:%Y-%m-%d %H:%M}] {actor_str} → {self.action}"
