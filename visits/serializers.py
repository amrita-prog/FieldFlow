"""
visits/serializers.py

Serializers for Visit list, detail (with nested AI output),
create, notes update, and lifecycle actions.
"""

from rest_framework import serializers
from visits.models import Visit, AIOutput
from tasks.models import Task
from accounts.models import User
from accounts.serializers import UserBriefSerializer


# ─────────────────────────────────────────────────────────────
# Task Brief (for nested display in visit detail)
# ─────────────────────────────────────────────────────────────

class TaskBriefSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = ['id', 'title', 'status', 'priority']


# ─────────────────────────────────────────────────────────────
# AI Output
# ─────────────────────────────────────────────────────────────

class AIOutputSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIOutput
        fields = ['summary', 'follow_up', 'risk_flag', 'generated_at']


# ─────────────────────────────────────────────────────────────
# Visit List (lightweight)
# ─────────────────────────────────────────────────────────────

class VisitListSerializer(serializers.ModelSerializer):
    agent = UserBriefSerializer(read_only=True)
    task_title = serializers.CharField(source='task.title', read_only=True, default=None)
    risk_flag = serializers.CharField(source='ai_output.risk_flag', read_only=True, default=None)

    class Meta:
        model = Visit
        fields = [
            'id', 'agent', 'location', 'status', 'outcome',
            'task_title', 'risk_flag',
            'started_at', 'completed_at', 'created_at',
        ]


# ─────────────────────────────────────────────────────────────
# Visit Detail (full, with nested AI output)
# ─────────────────────────────────────────────────────────────

class VisitDetailSerializer(serializers.ModelSerializer):
    agent = UserBriefSerializer(read_only=True)
    task = TaskBriefSerializer(read_only=True)
    ai_output = AIOutputSerializer(read_only=True)

    class Meta:
        model = Visit
        fields = [
            'id', 'task', 'agent', 'location',
            'status', 'outcome', 'notes',
            'started_at', 'completed_at',
            'created_at', 'updated_at',
            'ai_output',
        ]


# ─────────────────────────────────────────────────────────────
# Visit Create
# ─────────────────────────────────────────────────────────────

class VisitCreateSerializer(serializers.ModelSerializer):
    task_id = serializers.PrimaryKeyRelatedField(
        queryset=Task.objects.all(),
        source='task',
        required=False,
        allow_null=True,
    )
    agent_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        source='agent',
        required=False,
    )

    class Meta:
        model = Visit
        fields = ['task_id', 'agent_id', 'location']

    def validate_agent_id(self, user):
        """Only Field Agents can be assigned as visit agents."""
        if user and (not user.role or user.role.name != 'Field Agent'):
            raise serializers.ValidationError(
                f'{user.email} is not a Field Agent.'
            )
        return user

    def create(self, validated_data):
        request = self.context.get('request')
        user = request.user

        # If no agent specified and the requester is a Field Agent,
        # default the agent to the requester themselves
        if not validated_data.get('agent'):
            if user.role and user.role.name == 'Field Agent':
                validated_data['agent'] = user
            else:
                raise serializers.ValidationError(
                    {'agent_id': 'agent_id is required when created by a non-Field-Agent.'}
                )

        return Visit.objects.create(**validated_data)


# ─────────────────────────────────────────────────────────────
# Visit Notes + Outcome Update (triggers AI generation)
# ─────────────────────────────────────────────────────────────

class VisitNotesSerializer(serializers.Serializer):
    notes = serializers.CharField(min_length=5, max_length=5000)
    outcome = serializers.ChoiceField(
        choices=Visit.OUTCOME_CHOICES,
        required=False,
    )

    def validate_notes(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError('Notes cannot be blank.')
        return value.strip()


# ─────────────────────────────────────────────────────────────
# Visit Complete (requires outcome)
# ─────────────────────────────────────────────────────────────

class VisitCompleteSerializer(serializers.Serializer):
    outcome = serializers.ChoiceField(choices=Visit.OUTCOME_CHOICES)

    def validate_outcome(self, value):
        if value == Visit.OUTCOME_PENDING:
            raise serializers.ValidationError(
                'Cannot complete a visit with outcome "pending". '
                'Choose: successful, failed, or partial.'
            )
        return value
