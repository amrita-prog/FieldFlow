from django.contrib import admin
from tasks.models import Task

@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'status', 'priority', 'assigned_to', 'region', 'team', 'due_date', 'created_at')
    list_filter = ('status', 'priority', 'region', 'team')
    search_fields = ('title', 'description', 'assigned_to__username', 'assigned_to__email')
    date_hierarchy = 'created_at'
