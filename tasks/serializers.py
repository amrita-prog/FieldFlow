"""
tasks/serializers.py

Serializers for Task list, detail, create, assign, and status update.
"""

from datetime import date
from rest_framework import serializers
from tasks.models import Task
from accounts.models import User, Region, Team
from accounts.serializers import UserBriefSerializer, RegionSerializer, TeamSerializer


# ─────────────────────────────────────────────────────────────
# Task List (lightweight — for list views)
# ─────────────────────────────────────────────────────────────

class TaskListSerializer(serializers.ModelSerializer):
    assigned_to = UserBriefSerializer(read_only=True)
    created_by = UserBriefSerializer(read_only=True)
    region_name = serializers.CharField(source='region.name', read_only=True, default=None)
    team_name = serializers.CharField(source='team.name', read_only=True, default=None)

    class Meta:
        model = Task
        fields = [
            'id', 'title', 'status', 'priority',
            'assigned_to', 'created_by',
            'region_name', 'team_name',
            'due_date', 'created_at', 'updated_at',
        ]


# ─────────────────────────────────────────────────────────────
# Task Detail (full — for retrieve view)
# ─────────────────────────────────────────────────────────────

class TaskDetailSerializer(serializers.ModelSerializer):
    assigned_to = UserBriefSerializer(read_only=True)
    created_by = UserBriefSerializer(read_only=True)
    region = RegionSerializer(read_only=True)
    team = TeamSerializer(read_only=True)

    class Meta:
        model = Task
        fields = [
            'id', 'title', 'description', 'status', 'priority',
            'created_by', 'assigned_to',
            'region', 'team',
            'due_date', 'created_at', 'updated_at',
        ]


# ─────────────────────────────────────────────────────────────
# Task Create
# ─────────────────────────────────────────────────────────────

class TaskCreateSerializer(serializers.ModelSerializer):
    region_id = serializers.PrimaryKeyRelatedField(
        queryset=Region.objects.all(),
        source='region',
        required=False,
        allow_null=True,
    )
    team_id = serializers.PrimaryKeyRelatedField(
        queryset=Team.objects.all(),
        source='team',
        required=False,
        allow_null=True,
    )
    assigned_to_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        source='assigned_to',
        required=False,
        allow_null=True,
    )

    class Meta:
        model = Task
        fields = [
            'title', 'description', 'priority',
            'due_date', 'region_id', 'team_id', 'assigned_to_id',
        ]

    def validate_due_date(self, value):
        if value and value < date.today():
            raise serializers.ValidationError('Due date cannot be in the past.')
        return value

    def validate_assigned_to_id(self, user):
        """The assigned user must be a Field Agent."""
        if user and (not user.role or user.role.name != 'Field Agent'):
            raise serializers.ValidationError(
                f'Tasks can only be assigned to Field Agents. '
                f'{user.email} has role: {user.role.name if user.role else "None"}.'
            )
        return user

    def create(self, validated_data):
        request = self.context.get('request')
        user = request.user

        # Auto-set created_by
        validated_data['created_by'] = user

        assigned_to = validated_data.get('assigned_to')

        # Auto-fill region/team from assigned_to agent if provided
        if assigned_to:
            if not validated_data.get('region') and assigned_to.region:
                validated_data['region'] = assigned_to.region
            if not validated_data.get('team') and assigned_to.team:
                validated_data['team'] = assigned_to.team
        else:
            # Fallback to creator's region/team
            if not validated_data.get('region') and user.region:
                validated_data['region'] = user.region
            if not validated_data.get('team') and user.team:
                validated_data['team'] = user.team

        return Task.objects.create(**validated_data)


# ─────────────────────────────────────────────────────────────
# Task Assign
# ─────────────────────────────────────────────────────────────

class TaskAssignSerializer(serializers.Serializer):
    assigned_to_id = serializers.UUIDField()

    def validate_assigned_to_id(self, value):
        try:
            user = User.objects.select_related('role', 'region', 'team').get(pk=value)
        except User.DoesNotExist:
            raise serializers.ValidationError('User not found.')

        if not user.role or user.role.name != 'Field Agent':
            raise serializers.ValidationError(
                f'{user.email} is not a Field Agent (role: {user.role.name if user.role else "None"}).'
            )

        if not user.is_active:
            raise serializers.ValidationError(f'{user.email} is not an active user.')

        return user

    def validate(self, attrs):
        """
        Scope check: the agent must be within the caller's allowed scope.
        Caller's scope is determined by their ModulePermission for 'tasks'.
        """
        request = self.context.get('request')
        caller = request.user
        agent = attrs['assigned_to_id']  # already a User object after validate_assigned_to_id

        from accounts.models import ModulePermission
        try:
            perm = ModulePermission.objects.get(role=caller.role, module='tasks')
        except ModulePermission.DoesNotExist:
            raise serializers.ValidationError('You do not have task permissions.')

        scope = perm.scope

        if scope == 'all':
            pass  # Admin can assign anyone
        elif scope == 'region':
            if agent.region != caller.region:
                raise serializers.ValidationError(
                    f'You can only assign tasks to agents in your region ({caller.region}).'
                )
        elif scope == 'team':
            if agent.team != caller.team:
                raise serializers.ValidationError(
                    f'You can only assign tasks to agents in your team ({caller.team}).'
                )
        else:
            raise serializers.ValidationError('You do not have permission to assign tasks.')

        return attrs


# ─────────────────────────────────────────────────────────────
# Task Status Update
# ─────────────────────────────────────────────────────────────

class TaskStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=Task.STATUS_CHOICES)

    def validate(self, attrs):
        task = self.context.get('task')
        new_status = attrs['status']

        if not task.can_transition_to(new_status):
            allowed = Task.VALID_STATUS_TRANSITIONS.get(task.status, [])
            raise serializers.ValidationError({
                'status': (
                    f'Cannot move task from "{task.status}" to "{new_status}". '
                    f'Allowed transitions: {allowed if allowed else "none (terminal state)"}.'
                )
            })
        return attrs
