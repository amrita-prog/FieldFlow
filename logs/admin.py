from django.contrib import admin
from logs.models import ActivityLog


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ['timestamp', 'actor', 'action', 'target_type', 'target_id']
    list_filter = ['action', 'target_type']
    search_fields = ['actor__email', 'target_id']
    ordering = ['-timestamp']
    readonly_fields = ['id', 'actor', 'action', 'target_type', 'target_id', 'metadata', 'timestamp']
