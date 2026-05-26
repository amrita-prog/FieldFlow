"""
visits/models.py

Visit — tracks a field agent's physical visit to a location.
AIOutput — stores the mocked AI analysis of the visit notes.

Visit state machine:
    scheduled → in_progress → completed
                     ↓
                 cancelled
"""

import uuid
from django.db import models
from accounts.models import User
from tasks.models import Task


class Visit(models.Model):

    # ── Status choices ────────────────────────────────────────
    STATUS_SCHEDULED = 'scheduled'
    STATUS_IN_PROGRESS = 'in_progress'
    STATUS_COMPLETED = 'completed'
    STATUS_CANCELLED = 'cancelled'

    STATUS_CHOICES = [
        (STATUS_SCHEDULED,   'Scheduled'),
        (STATUS_IN_PROGRESS, 'In Progress'),
        (STATUS_COMPLETED,   'Completed'),
        (STATUS_CANCELLED,   'Cancelled'),
    ]

    # ── Outcome choices ───────────────────────────────────────
    OUTCOME_SUCCESSFUL = 'successful'
    OUTCOME_FAILED = 'failed'
    OUTCOME_PARTIAL = 'partial'
    OUTCOME_PENDING = 'pending'

    OUTCOME_CHOICES = [
        (OUTCOME_SUCCESSFUL, 'Successful'),
        (OUTCOME_FAILED,     'Failed'),
        (OUTCOME_PARTIAL,    'Partial'),
        (OUTCOME_PENDING,    'Pending'),
    ]

    # ── Valid state transitions ───────────────────────────────
    VALID_STATUS_TRANSITIONS = {
        STATUS_SCHEDULED:   [STATUS_IN_PROGRESS, STATUS_CANCELLED],
        STATUS_IN_PROGRESS: [STATUS_COMPLETED,   STATUS_CANCELLED],
        STATUS_COMPLETED:   [],
        STATUS_CANCELLED:   [],
    }

    # ── Fields ────────────────────────────────────────────────
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    task = models.ForeignKey(
        Task,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='visits',
    )
    agent = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='visits',
    )

    location = models.CharField(max_length=255)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_SCHEDULED,
    )
    notes = models.TextField(blank=True, default='')
    outcome = models.CharField(
        max_length=20,
        choices=OUTCOME_CHOICES,
        default=OUTCOME_PENDING,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Visit by {self.agent} at {self.location} [{self.status}]"

    def can_transition_to(self, new_status):
        """Returns True if the status transition is allowed."""
        return new_status in self.VALID_STATUS_TRANSITIONS.get(self.status, [])


class AIOutput(models.Model):
    """
    Stores the mocked AI analysis generated after visit notes are submitted.
    One-to-one with Visit — regenerated on subsequent note updates.
    """

    RISK_LOW = 'low'
    RISK_MEDIUM = 'medium'
    RISK_HIGH = 'high'

    RISK_CHOICES = [
        (RISK_LOW,    'Low'),
        (RISK_MEDIUM, 'Medium'),
        (RISK_HIGH,   'High'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    visit = models.OneToOneField(
        Visit,
        on_delete=models.CASCADE,
        related_name='ai_output',
    )

    summary = models.TextField()
    follow_up = models.TextField()
    risk_flag = models.CharField(max_length=10, choices=RISK_CHOICES, default=RISK_LOW)
    generated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-generated_at']

    def __str__(self):
        return f"AI Output for Visit {self.visit_id} [risk: {self.risk_flag}]"
