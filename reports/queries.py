"""
reports/queries.py

Raw SQL query functions for all reporting endpoints.

Design rules:
  - All queries use parameterized placeholders (%s) — no f-string SQL.
  - Every function accepts optional scope params (region_id, team_id)
    that are injected as WHERE clauses when provided.
  - Returns list of plain dicts for easy JSON serialization.
"""

from django.db import connection


def _dictfetchall(cursor):
    """Convert cursor rows to list of dicts using column names."""
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


# ─────────────────────────────────────────────────────────────
# Report 1: Pending Tasks by Region and Team
# ─────────────────────────────────────────────────────────────

def get_pending_tasks_by_region(region_id=None, team_id=None):
    """
    Returns pending task counts grouped by region and team.
    Optionally scoped to a specific region or team.
    """
    where_clauses = ["t.status = 'pending'"]
    params = []

    if region_id:
        where_clauses.append("t.region_id = %s")
        params.append(str(region_id))
    if team_id:
        where_clauses.append("t.team_id = %s")
        params.append(str(team_id))

    where_sql = " AND ".join(where_clauses)

    sql = f"""
        SELECT
            r.name                                              AS region,
            tm.name                                             AS team,
            COUNT(t.id)                                         AS pending_count,
            COUNT(CASE WHEN t.priority IN ('high','critical')
                       THEN 1 END)                              AS high_priority_count,
            MIN(t.due_date)                                     AS earliest_due_date
        FROM tasks_task t
        LEFT JOIN accounts_region r  ON t.region_id = r.id
        LEFT JOIN accounts_team  tm  ON t.team_id   = tm.id
        WHERE {where_sql}
        GROUP BY r.name, tm.name
        ORDER BY pending_count DESC, high_priority_count DESC
    """

    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        return _dictfetchall(cursor)


# ─────────────────────────────────────────────────────────────
# Report 2: Average Task Completion Time per Field Agent
# ─────────────────────────────────────────────────────────────

def get_agent_performance(region_id=None, team_id=None):
    """
    Returns average task completion time per field agent.
    Completion time = updated_at - created_at for completed tasks.
    """
    where_clauses = ["t.status = 'completed'", "r.name = 'Field Agent'"]
    params = []

    if region_id:
        where_clauses.append("u.region_id = %s")
        params.append(str(region_id))
    if team_id:
        where_clauses.append("u.team_id = %s")
        params.append(str(team_id))

    where_sql = " AND ".join(where_clauses)

    sql = f"""
        SELECT
            u.id                                                AS agent_id,
            u.username                                          AS agent_username,
            u.email                                             AS agent_email,
            COUNT(t.id)                                         AS total_completed,
            ROUND(
                AVG(
                    (JULIANDAY(t.updated_at) - JULIANDAY(t.created_at)) * 24
                ), 2
            )                                                   AS avg_hours_to_complete,
            COUNT(CASE WHEN t.priority IN ('high','critical')
                       THEN 1 END)                              AS high_priority_completed
        FROM tasks_task t
        JOIN accounts_user u   ON t.assigned_to_id = u.id
        JOIN accounts_role r   ON u.role_id = r.id
        WHERE {where_sql}
        GROUP BY u.id, u.username, u.email
        ORDER BY avg_hours_to_complete ASC
    """

    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        return _dictfetchall(cursor)


# ─────────────────────────────────────────────────────────────
# Report 3: Visits Completed in the Last N Days
# ─────────────────────────────────────────────────────────────

def get_recent_visits(days=7, region_id=None, team_id=None):
    """
    Returns visits completed in the last `days` days, with agent stats.
    """
    where_clauses = [
        "v.status = 'completed'",
        f"v.completed_at >= DATETIME('now', '-{int(days)} days')",
    ]
    params = []

    if region_id:
        where_clauses.append("u.region_id = %s")
        params.append(str(region_id))
    if team_id:
        where_clauses.append("u.team_id = %s")
        params.append(str(team_id))

    where_sql = " AND ".join(where_clauses)

    sql = f"""
        SELECT
            u.username                                              AS agent,
            u.email                                                 AS agent_email,
            tm.name                                                 AS team,
            r.name                                                  AS region,
            COUNT(v.id)                                             AS visits_completed,
            COUNT(CASE WHEN v.outcome = 'successful' THEN 1 END)    AS successful,
            COUNT(CASE WHEN v.outcome = 'failed'     THEN 1 END)    AS failed,
            COUNT(CASE WHEN v.outcome = 'partial'    THEN 1 END)    AS partial,
            ROUND(
                AVG(
                    (JULIANDAY(v.completed_at) - JULIANDAY(v.started_at)) * 1440
                ), 2
            )                                                       AS avg_visit_minutes
        FROM visits_visit v
        JOIN accounts_user   u  ON v.agent_id    = u.id
        LEFT JOIN accounts_team   tm ON u.team_id   = tm.id
        LEFT JOIN accounts_region r  ON u.region_id = r.id
        WHERE {where_sql}
        GROUP BY u.username, u.email, tm.name, r.name
        ORDER BY visits_completed DESC
    """

    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        return _dictfetchall(cursor)


# ─────────────────────────────────────────────────────────────
# Report 4: Task Status Distribution by Manager
# ─────────────────────────────────────────────────────────────

def get_task_distribution(region_id=None, team_id=None):
    """
    Returns task status breakdown per manager (created_by).
    """
    where_clauses = ["1=1"]
    params = []

    if region_id:
        where_clauses.append("t.region_id = %s")
        params.append(str(region_id))
    if team_id:
        where_clauses.append("t.team_id = %s")
        params.append(str(team_id))

    where_sql = " AND ".join(where_clauses)

    sql = f"""
        SELECT
            u.username              AS manager,
            u.email                 AS manager_email,
            t.status                AS status,
            COUNT(*)                AS task_count
        FROM tasks_task t
        JOIN accounts_user u ON t.created_by_id = u.id
        WHERE {where_sql}
        GROUP BY u.username, u.email, t.status
        ORDER BY u.username, t.status
    """

    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        return _dictfetchall(cursor)


# ─────────────────────────────────────────────────────────────
# Dashboard Summary (ORM-based for flexibility)
# ─────────────────────────────────────────────────────────────

def get_dashboard_summary(user):
    """
    Returns scoped summary counts for the dashboard.
    Uses Django ORM for clarity and maintainability.
    """
    from tasks.models import Task
    from visits.models import Visit
    from django.utils import timezone
    from datetime import timedelta
    from accounts.models import ModulePermission

    # Build scoped querysets
    tasks_qs = Task.objects.all()
    visits_qs = Visit.objects.all()

    # Apply scope based on role
    role_name = user.role.name if user.role else None

    if role_name == 'Regional Manager' and user.region:
        tasks_qs = tasks_qs.filter(region=user.region)
        visits_qs = visits_qs.filter(agent__region=user.region)
    elif role_name == 'Team Lead' and user.team:
        tasks_qs = tasks_qs.filter(team=user.team)
        visits_qs = visits_qs.filter(agent__team=user.team)
    elif role_name == 'Field Agent':
        tasks_qs = tasks_qs.filter(assigned_to=user)
        visits_qs = visits_qs.filter(agent=user)

    # Task counts
    week_ago = timezone.now() - timedelta(days=7)
    today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)

    from visits.models import AIOutput

    return {
        'tasks': {
            'total': tasks_qs.count(),
            'pending': tasks_qs.filter(status='pending').count(),
            'in_progress': tasks_qs.filter(status='in_progress').count(),
            'completed': tasks_qs.filter(status='completed').count(),
            'cancelled': tasks_qs.filter(status='cancelled').count(),
            'overdue': tasks_qs.filter(
                due_date__lt=timezone.now().date(),
                status__in=['pending', 'in_progress']
            ).count(),
        },
        'visits': {
            'total': visits_qs.count(),
            'scheduled': visits_qs.filter(status='scheduled').count(),
            'in_progress': visits_qs.filter(status='in_progress').count(),
            'completed_this_week': visits_qs.filter(
                status='completed',
                completed_at__gte=week_ago,
            ).count(),
            'high_risk': AIOutput.objects.filter(
                visit__in=visits_qs,
                risk_flag='high',
            ).count(),
        },
        'role': role_name,
        'scope': {
            'region': str(user.region) if user.region else None,
            'team': str(user.team) if user.team else None,
        },
    }
