"""
tasks/filters.py

django-filter FilterSet for Task list endpoint.
Supports filtering by status, priority, assigned_to,
region, team, due_date range.
"""

import django_filters
from tasks.models import Task


class TaskFilter(django_filters.FilterSet):
    # Exact matches
    status = django_filters.ChoiceFilter(choices=Task.STATUS_CHOICES)
    priority = django_filters.ChoiceFilter(choices=Task.PRIORITY_CHOICES)
    assigned_to = django_filters.UUIDFilter(field_name='assigned_to__id')
    created_by = django_filters.UUIDFilter(field_name='created_by__id')
    region = django_filters.UUIDFilter(field_name='region__id')
    team = django_filters.UUIDFilter(field_name='team__id')

    # Date range filters for due_date
    due_date = django_filters.DateFilter(field_name='due_date')
    due_date_before = django_filters.DateFilter(field_name='due_date', lookup_expr='lte')
    due_date_after = django_filters.DateFilter(field_name='due_date', lookup_expr='gte')

    # Overdue tasks shortcut
    overdue = django_filters.BooleanFilter(method='filter_overdue')

    class Meta:
        model = Task
        fields = [
            'status', 'priority', 'assigned_to', 'created_by',
            'region', 'team', 'due_date',
        ]

    def filter_overdue(self, queryset, name, value):
        from datetime import date
        if value:
            return queryset.filter(
                due_date__lt=date.today(),
                status__in=[Task.STATUS_PENDING, Task.STATUS_IN_PROGRESS],
            )
        return queryset
