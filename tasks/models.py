"""
tasks/models.py

Task model with scope fields (region, team), assignment,
status/priority choices, and valid state transition map.
"""

import uuid
from django.db import models
from accounts.models import User, Region, Team


class Task(models.Model):

    # ── Status choices ────────────────────────────────────────
    STATUS_PENDING = 'pending'
    STATUS_IN_PROGRESS = 'in_progress'
    STATUS_COMPLETED = 'completed'
    STATUS_CANCELLED = 'cancelled'

    STATUS_CHOICES = [
        (STATUS_PENDING,     'Pending'),
        (STATUS_IN_PROGRESS, 'In Progress'),
        (STATUS_COMPLETED,   'Completed'),
        (STATUS_CANCELLED,   'Cancelled'),
    ]

    # ── Priority choices ──────────────────────────────────────
    PRIORITY_LOW = 'low'
    PRIORITY_MEDIUM = 'medium'
    PRIORITY_HIGH = 'high'
    PRIORITY_CRITICAL = 'critical'

    PRIORITY_CHOICES = [
        (PRIORITY_LOW,      'Low'),
        (PRIORITY_MEDIUM,   'Medium'),
        (PRIORITY_HIGH,     'High'),
        (PRIORITY_CRITICAL, 'Critical'),
    ]

    # ── Valid status transitions ───────────────────────────────
    # Only these moves are allowed; anything else returns 400.
    VALID_STATUS_TRANSITIONS = {
        STATUS_PENDING:     [STATUS_IN_PROGRESS, STATUS_CANCELLED],
        STATUS_IN_PROGRESS: [STATUS_COMPLETED,   STATUS_CANCELLED],
        STATUS_COMPLETED:   [],
        STATUS_CANCELLED:   [],
    }

    # ── Fields ────────────────────────────────────────────────
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_tasks',
    )
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_tasks',
    )

    region = models.ForeignKey(
        Region,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tasks',
    )
    team = models.ForeignKey(
        Team,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tasks',
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
    )
    priority = models.CharField(
        max_length=10,
        choices=PRIORITY_CHOICES,
        default=PRIORITY_MEDIUM,
    )

    due_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.status.upper()}] {self.title}"

    def can_transition_to(self, new_status):
        """Returns True if the status transition is allowed."""
        return new_status in self.VALID_STATUS_TRANSITIONS.get(self.status, [])
