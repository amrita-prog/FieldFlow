"""
logs/utils.py

log_activity() — central logging utility.

Rules:
  - Never raises an exception (wrapped in try/except).
  - Safe to call before the logs migration has run (fails silently).
  - Called from tasks/views.py, visits/views.py, and accounts/views.py.
"""


def log_activity(actor, action: str, target, metadata: dict = None):
    """
    Create an ActivityLog record.

    Args:
        actor:    The User who performed the action.
        action:   An ActionTypes string, e.g. 'task_created'.
        target:   The model instance the action was performed on.
        metadata: Optional dict with extra context (old/new status, etc.)
    """
    try:
        from logs.models import ActivityLog

        ActivityLog.objects.create(
            actor=actor,
            action=action,
            target_type=target.__class__.__name__.lower(),
            target_id=str(getattr(target, 'id', '')),
            metadata=metadata or {},
        )
    except Exception:
        # Logging must NEVER crash the main request flow.
        pass
