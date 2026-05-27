from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DefaultUserAdmin
from accounts.models import User, Role, Region, Team, ModulePermission, EmployeeProfile

@admin.register(User)
class UserAdmin(DefaultUserAdmin):
    list_display = ('id', 'username', 'email', 'first_name', 'last_name', 'role', 'is_active', 'is_staff')
    list_filter = ('role', 'is_active', 'is_staff', 'is_superuser', 'region', 'team')
    search_fields = ('id', 'username', 'email', 'first_name', 'last_name')
    readonly_fields = ('id',)
    fieldsets = DefaultUserAdmin.fieldsets + (
        ('Custom Fields', {'fields': ('role', 'region', 'team')}),
    )
    add_fieldsets = DefaultUserAdmin.add_fieldsets + (
        ('Custom Fields', {'fields': ('role', 'region', 'team')}),
    )

@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'description')
    search_fields = ('name',)

@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'manager')
    search_fields = ('name',)

@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'region', 'lead')
    search_fields = ('name',)
    list_filter = ('region',)

@admin.register(ModulePermission)
class ModulePermissionAdmin(admin.ModelAdmin):
    list_display = ('id', 'role', 'module', 'scope', 'can_create', 'can_read', 'can_update', 'can_delete')
    list_filter = ('role', 'module', 'scope')

@admin.register(EmployeeProfile)
class EmployeeProfileAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'employee_code', 'phone', 'joining_date')
    search_fields = ('user__username', 'user__email', 'employee_code', 'phone')
