"""
logs/serializers.py
"""

from rest_framework import serializers
from logs.models import ActivityLog
from accounts.serializers import UserBriefSerializer


class ActivityLogSerializer(serializers.ModelSerializer):
    actor = UserBriefSerializer(read_only=True)

    class Meta:
        model = ActivityLog
        fields = [
            'id', 'actor', 'action',
            'target_type', 'target_id',
            'metadata', 'timestamp',
        ]
