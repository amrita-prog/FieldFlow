from django.contrib import admin
from visits.models import Visit, AIOutput

@admin.register(Visit)
class VisitAdmin(admin.ModelAdmin):
    list_display = ('id', 'task', 'agent', 'location', 'status', 'outcome', 'started_at', 'completed_at', 'created_at')
    list_filter = ('status', 'outcome')
    search_fields = ('location', 'notes', 'agent__username', 'agent__email', 'task__title')
    date_hierarchy = 'created_at'

@admin.register(AIOutput)
class AIOutputAdmin(admin.ModelAdmin):
    list_display = ('id', 'visit', 'risk_flag', 'generated_at')
    list_filter = ('risk_flag',)
    search_fields = ('summary', 'follow_up', 'visit__location')
    date_hierarchy = 'generated_at'
