from django.contrib import admin
from logs.models import ActivityLog

@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'actor', 'action', 'target_type', 'target_id', 'timestamp')
    list_filter = ('action', 'target_type')
    search_fields = ('action', 'target_type', 'target_id', 'actor__username', 'actor__email')
    date_hierarchy = 'timestamp'
