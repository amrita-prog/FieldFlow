"""
visits/filters.py

FilterSet for Visit list endpoint.
"""

import django_filters
from visits.models import Visit


class VisitFilter(django_filters.FilterSet):
    status = django_filters.ChoiceFilter(choices=Visit.STATUS_CHOICES)
    outcome = django_filters.ChoiceFilter(choices=Visit.OUTCOME_CHOICES)
    agent = django_filters.UUIDFilter(field_name='agent__id')
    task = django_filters.UUIDFilter(field_name='task__id')

    # Date range filters on completed_at
    completed_after = django_filters.DateTimeFilter(
        field_name='completed_at', lookup_expr='gte'
    )
    completed_before = django_filters.DateTimeFilter(
        field_name='completed_at', lookup_expr='lte'
    )

    # AI risk flag filter (joins ai_output)
    risk_flag = django_filters.CharFilter(field_name='ai_output__risk_flag')

    class Meta:
        model = Visit
        fields = ['status', 'outcome', 'agent', 'task']
