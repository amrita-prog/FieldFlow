"""
reports/views.py

All reporting endpoints. Each view:
  1. Checks role-based access (Field Agent always 403)
  2. Derives scope params from the requesting user's role/region/team
  3. Passes those params to a query function in queries.py
  4. Returns the result as JSON

Access matrix:
  Admin          → all data
  Regional Mgr   → scoped to their region
  Team Lead      → scoped to their team
  Auditor        → all data (read-only)
  Field Agent    → 403 on all report endpoints
"""

from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from reports.queries import (
    get_pending_tasks_by_region,
    get_agent_performance,
    get_recent_visits,
    get_task_distribution,
    get_dashboard_summary,
)


# ─────────────────────────────────────────────────────────────
# Base helper
# ─────────────────────────────────────────────────────────────

def _get_scope_params(user):
    """
    Returns (region_id, team_id) based on user's role.
    Admin and Auditor get (None, None) → no scope filtering.
    """
    role_name = user.role.name if user.role else None

    if role_name == 'Regional Manager':
        return (user.region_id if user.region else None, None)
    elif role_name == 'Team Lead':
        return (None, user.team_id if user.team else None)

    # Admin, Auditor → full access
    return (None, None)


def _check_report_access(user):
    """
    Returns a Response error if the user cannot access reports,
    or None if access is granted.
    """
    role_name = user.role.name if user.role else None
    if role_name == 'Field Agent' or role_name is None:
        return Response(
            {
                'error': True,
                'code': 'PERMISSION_DENIED',
                'message': 'Field Agents do not have access to reports.',
            },
            status=status.HTTP_403_FORBIDDEN,
        )
    return None


# ─────────────────────────────────────────────────────────────
# Dashboard Summary
# ─────────────────────────────────────────────────────────────

class DashboardSummaryView(APIView):
    """
    GET /api/reports/dashboard-summary/
    All roles (Field Agent gets their own scoped data).
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        data = get_dashboard_summary(request.user)
        return Response(data, status=status.HTTP_200_OK)


# ─────────────────────────────────────────────────────────────
# Report 1: Pending Tasks by Region / Team
# ─────────────────────────────────────────────────────────────

class PendingTasksView(APIView):
    """
    GET /api/reports/pending-tasks/
    Optional query params: ?days=7
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        error = _check_report_access(request.user)
        if error:
            return error

        region_id, team_id = _get_scope_params(request.user)
        data = get_pending_tasks_by_region(region_id=region_id, team_id=team_id)

        return Response({
            'count': len(data),
            'results': data,
        }, status=status.HTTP_200_OK)


# ─────────────────────────────────────────────────────────────
# Report 2: Agent Performance
# ─────────────────────────────────────────────────────────────

class AgentPerformanceView(APIView):
    """
    GET /api/reports/agent-performance/
    Average task completion time per field agent.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        error = _check_report_access(request.user)
        if error:
            return error

        region_id, team_id = _get_scope_params(request.user)
        data = get_agent_performance(region_id=region_id, team_id=team_id)

        return Response({
            'count': len(data),
            'results': data,
        }, status=status.HTTP_200_OK)


# ─────────────────────────────────────────────────────────────
# Report 3: Recent Visits
# ─────────────────────────────────────────────────────────────

class RecentVisitsView(APIView):
    """
    GET /api/reports/recent-visits/
    Optional: ?days=7 (default 7)
    Visits completed in the last N days.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        error = _check_report_access(request.user)
        if error:
            return error

        try:
            days = int(request.query_params.get('days', 7))
            if days < 1 or days > 365:
                days = 7
        except (ValueError, TypeError):
            days = 7

        region_id, team_id = _get_scope_params(request.user)
        data = get_recent_visits(days=days, region_id=region_id, team_id=team_id)

        return Response({
            'period_days': days,
            'count': len(data),
            'results': data,
        }, status=status.HTTP_200_OK)


# ─────────────────────────────────────────────────────────────
# Report 4: Task Status Distribution
# ─────────────────────────────────────────────────────────────

class TaskDistributionView(APIView):
    """
    GET /api/reports/task-distribution/
    Task status breakdown grouped by the manager who created them.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        error = _check_report_access(request.user)
        if error:
            return error

        region_id, team_id = _get_scope_params(request.user)
        data = get_task_distribution(region_id=region_id, team_id=team_id)

        # Pivot data: group by manager for easier frontend rendering
        pivoted = {}
        for row in data:
            mgr = row['manager']
            if mgr not in pivoted:
                pivoted[mgr] = {
                    'manager': mgr,
                    'manager_email': row['manager_email'],
                    'statuses': {},
                    'total': 0,
                }
            pivoted[mgr]['statuses'][row['status']] = row['task_count']
            pivoted[mgr]['total'] += row['task_count']

        return Response({
            'count': len(pivoted),
            'results': list(pivoted.values()),
        }, status=status.HTTP_200_OK)
