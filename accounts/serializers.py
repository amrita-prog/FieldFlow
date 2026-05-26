"""
accounts/serializers.py

Serializers for auth, user, role, region, team, and permissions.
"""

from django.contrib.auth import authenticate
from rest_framework import serializers
from accounts.models import User, Role, Region, Team, ModulePermission, EmployeeProfile


# ─────────────────────────────────────────────────────────────
# Role
# ─────────────────────────────────────────────────────────────

class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = ['id', 'name', 'description']


# ─────────────────────────────────────────────────────────────
# Region
# ─────────────────────────────────────────────────────────────

class RegionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Region
        fields = ['id', 'name']


# ─────────────────────────────────────────────────────────────
# Team
# ─────────────────────────────────────────────────────────────

class TeamSerializer(serializers.ModelSerializer):
    region = RegionSerializer(read_only=True)

    class Meta:
        model = Team
        fields = ['id', 'name', 'region']


# ─────────────────────────────────────────────────────────────
# Module Permission
# ─────────────────────────────────────────────────────────────

class ModulePermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ModulePermission
        fields = ['module', 'can_create', 'can_read', 'can_update', 'can_delete', 'scope']


# ─────────────────────────────────────────────────────────────
# Employee Profile
# ─────────────────────────────────────────────────────────────

class EmployeeProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployeeProfile
        fields = ['phone', 'employee_code', 'joining_date']


# ─────────────────────────────────────────────────────────────
# User — Brief (used as nested read-only in tasks, visits, logs)
# ─────────────────────────────────────────────────────────────

class UserBriefSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    role_name = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'full_name', 'role_name']


# ─────────────────────────────────────────────────────────────
# User — Full Detail
# ─────────────────────────────────────────────────────────────

class UserDetailSerializer(serializers.ModelSerializer):
    role = RoleSerializer(read_only=True)
    region = RegionSerializer(read_only=True)
    team = TeamSerializer(read_only=True)
    profile = EmployeeProfileSerializer(read_only=True)
    full_name = serializers.CharField(read_only=True)
    permissions = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'full_name', 'role', 'region', 'team', 'profile',
            'is_active', 'date_joined', 'last_login', 'permissions',
        ]

    def get_permissions(self, obj):
        if not obj.role:
            return []
        perms = ModulePermission.objects.filter(role=obj.role)
        return ModulePermissionSerializer(perms, many=True).data


# ─────────────────────────────────────────────────────────────
# User — Create (Admin use)
# ─────────────────────────────────────────────────────────────

class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)
    role_id = serializers.PrimaryKeyRelatedField(
        queryset=Role.objects.all(), source='role', write_only=True
    )
    region_id = serializers.PrimaryKeyRelatedField(
        queryset=Region.objects.all(), source='region',
        write_only=True, required=False, allow_null=True
    )
    team_id = serializers.PrimaryKeyRelatedField(
        queryset=Team.objects.all(), source='team',
        write_only=True, required=False, allow_null=True
    )

    class Meta:
        model = User
        fields = [
            'username', 'email', 'password',
            'first_name', 'last_name',
            'role_id', 'region_id', 'team_id',
        ]

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        # Create an empty profile
        EmployeeProfile.objects.create(
            user=user,
            employee_code=f"EMP{str(user.id)[:6].upper()}"
        )
        return user


# ─────────────────────────────────────────────────────────────
# User — Update (Admin use)
# ─────────────────────────────────────────────────────────────

class UserUpdateSerializer(serializers.ModelSerializer):
    role_id = serializers.PrimaryKeyRelatedField(
        queryset=Role.objects.all(), source='role',
        write_only=True, required=False
    )
    region_id = serializers.PrimaryKeyRelatedField(
        queryset=Region.objects.all(), source='region',
        write_only=True, required=False, allow_null=True
    )
    team_id = serializers.PrimaryKeyRelatedField(
        queryset=Team.objects.all(), source='team',
        write_only=True, required=False, allow_null=True
    )

    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'is_active',
            'role_id', 'region_id', 'team_id',
        ]


# ─────────────────────────────────────────────────────────────
# Login
# ─────────────────────────────────────────────────────────────

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')

        if not email or not password:
            raise serializers.ValidationError('Email and password are required.')

        # authenticate() needs username field; our USERNAME_FIELD is email
        user = authenticate(
            request=self.context.get('request'),
            email=email,
            password=password,
        )

        if not user:
            raise serializers.ValidationError('Invalid email or password.')

        if not user.is_active:
            raise serializers.ValidationError('This account has been deactivated.')

        attrs['user'] = user
        return attrs
