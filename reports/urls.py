"""
reports/urls.py
"""

from django.urls import path
from reports.views import (
    DashboardSummaryView,
    PendingTasksView,
    AgentPerformanceView,
    RecentVisitsView,
    TaskDistributionView,
)

urlpatterns = [
    path('reports/dashboard-summary/',  DashboardSummaryView.as_view(),  name='report-dashboard'),
    path('reports/pending-tasks/',      PendingTasksView.as_view(),       name='report-pending-tasks'),
    path('reports/agent-performance/',  AgentPerformanceView.as_view(),   name='report-agent-performance'),
    path('reports/recent-visits/',      RecentVisitsView.as_view(),       name='report-recent-visits'),
    path('reports/task-distribution/',  TaskDistributionView.as_view(),   name='report-task-distribution'),
]
