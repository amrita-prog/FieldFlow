"""
accounts/models.py

All user, role, permission, region, team, and profile models.
Order matters here due to FK dependencies:
  Role → (Region, Team reference User) → User → ModulePermission, EmployeeProfile
"""

import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser


# ─────────────────────────────────────────────────────────────
# Role
# ─────────────────────────────────────────────────────────────
class Role(models.Model):
    """
    The five system roles. Seeded — not created by users.
    """
    ADMIN = 'Admin'
    REGIONAL_MANAGER = 'Regional Manager'
    TEAM_LEAD = 'Team Lead'
    FIELD_AGENT = 'Field Agent'
    AUDITOR = 'Auditor'

    ROLE_CHOICES = [
        (ADMIN, 'Admin'),
        (REGIONAL_MANAGER, 'Regional Manager'),
        (TEAM_LEAD, 'Team Lead'),
        (FIELD_AGENT, 'Field Agent'),
        (AUDITOR, 'Auditor'),
    ]

    name = models.CharField(max_length=50, unique=True, choices=ROLE_CHOICES)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return self.name


# ─────────────────────────────────────────────────────────────
# Region
# ─────────────────────────────────────────────────────────────
class Region(models.Model):
    """
    Geographic region managed by a Regional Manager.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    # FK to User — set after User model is defined, uses string reference
    manager = models.ForeignKey(
        'User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='managed_regions',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


# ─────────────────────────────────────────────────────────────
# Team
# ─────────────────────────────────────────────────────────────
class Team(models.Model):
    """
    A team within a region, led by a Team Lead.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    region = models.ForeignKey(
        Region,
        on_delete=models.CASCADE,
        related_name='teams',
    )
    lead = models.ForeignKey(
        'User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='led_teams',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']
        unique_together = ('name', 'region')

    def __str__(self):
        return f"{self.name} ({self.region.name})"


# ─────────────────────────────────────────────────────────────
# User (Custom)
# ─────────────────────────────────────────────────────────────
class User(AbstractUser):
    """
    Extended user model with UUID PK, role, region, and team.
    AbstractUser provides: username, email, password, first_name,
    last_name, is_active, is_staff, date_joined, last_login.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    role = models.ForeignKey(
        Role,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users',
    )
    region = models.ForeignKey(
        Region,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users',
    )
    team = models.ForeignKey(
        Team,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='members',
    )
    # Use email as the login identifier alongside username
    email = models.EmailField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    USERNAME_FIELD = 'email'
    # username is still required for AbstractUser but email is the login field
    REQUIRED_FIELDS = ['username']

    class Meta:
        ordering = ['email']

    def __str__(self):
        return f"{self.email} ({self.role})"

    @property
    def full_name(self):
        name = f"{self.first_name} {self.last_name}".strip()
        return name if name else self.username

    @property
    def role_name(self):
        return self.role.name if self.role else None


# ─────────────────────────────────────────────────────────────
# Module Permission
# ─────────────────────────────────────────────────────────────
class ModulePermission(models.Model):
    """
    Defines what a role can do in each module.
    'scope' controls which records the role can see/act on.
    """
    SCOPE_OWN = 'own'
    SCOPE_TEAM = 'team'
    SCOPE_REGION = 'region'
    SCOPE_ALL = 'all'

    SCOPE_CHOICES = [
        (SCOPE_OWN, 'Own records only'),
        (SCOPE_TEAM, 'Team records'),
        (SCOPE_REGION, 'Region records'),
        (SCOPE_ALL, 'All records'),
    ]

    MODULE_TASKS = 'tasks'
    MODULE_VISITS = 'visits'
    MODULE_REPORTS = 'reports'
    MODULE_LOGS = 'logs'
    MODULE_USERS = 'users'

    MODULE_CHOICES = [
        (MODULE_TASKS, 'Tasks'),
        (MODULE_VISITS, 'Visits'),
        (MODULE_REPORTS, 'Reports'),
        (MODULE_LOGS, 'Logs'),
        (MODULE_USERS, 'Users'),
    ]

    role = models.ForeignKey(
        Role,
        on_delete=models.CASCADE,
        related_name='module_permissions',
    )
    module = models.CharField(max_length=20, choices=MODULE_CHOICES)
    can_create = models.BooleanField(default=False)
    can_read = models.BooleanField(default=False)
    can_update = models.BooleanField(default=False)
    can_delete = models.BooleanField(default=False)
    scope = models.CharField(max_length=10, choices=SCOPE_CHOICES, default=SCOPE_OWN)

    class Meta:
        unique_together = ('role', 'module')
        ordering = ['role', 'module']

    def __str__(self):
        return f"{self.role.name} → {self.module} (scope: {self.scope})"


# ─────────────────────────────────────────────────────────────
# Employee Profile
# ─────────────────────────────────────────────────────────────
class EmployeeProfile(models.Model):
    """
    Additional professional details for each user.
    One-to-one extension of User.
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile',
    )
    phone = models.CharField(max_length=20, blank=True)
    employee_code = models.CharField(max_length=20, unique=True)
    joining_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"Profile: {self.user.email} ({self.employee_code})"
